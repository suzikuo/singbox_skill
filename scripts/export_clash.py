from __future__ import annotations

import argparse
import base64
from pathlib import Path

from singbox_reader import (
    DEFAULT_CONF_DIR,
    ExportError,
    clean_params,
    dump_yaml,
    load_nodes,
    resolve_server,
    transport_type,
    warning,
)


def compact_options(values: dict) -> dict:
    result = {}
    for key, value in values.items():
        if value is None:
            continue
        if value == "":
            continue
        if value is False:
            continue
        if isinstance(value, list) and not value:
            continue
        result[key] = value
    return result


def build_proxy(node: dict, server: str) -> dict | None:
    protocol = node["protocol"]
    port = node["port"]
    proxy = {
        "name": node["name"],
        "server": server,
        "port": port,
    }

    if protocol == "vmess":
        proxy.update(
            {
                "type": "vmess",
                "uuid": node.get("uuid"),
                "alterId": 0,
                "cipher": "auto",
            }
        )
    elif protocol == "vless":
        proxy.update({"type": "vless", "uuid": node.get("uuid")})
    elif protocol == "trojan":
        proxy.update({"type": "trojan", "password": node.get("password")})
    elif protocol == "hysteria2":
        proxy.update(
            {
                "type": "hysteria2",
                "password": node.get("password"),
                "sni": node.get("server_name") or server,
                "skip-cert-verify": node["skip_cert_verify"],
            }
        )
    elif protocol == "tuic":
        proxy.update(
            {
                "type": "tuic",
                "uuid": node.get("uuid"),
                "password": node.get("password"),
                "congestion-controller": node.get("congestion_control") or "bbr",
                "udp-relay-mode": node.get("udp_relay_mode") or "native",
                "sni": node.get("server_name") or server,
                "skip-cert-verify": node["skip_cert_verify"],
            }
        )
    elif protocol == "shadowsocks":
        proxy.update(
            {
                "type": "ss",
                "cipher": node.get("method"),
                "password": node.get("password"),
            }
        )
    elif protocol == "socks":
        proxy.update(
            clean_params(
                {
                    "type": "socks5",
                    "username": node.get("username"),
                    "password": node.get("password"),
                }
            )
        )
    else:
        warning(f"clash export does not support protocol '{protocol}' for node '{node['name']}'")
        return None

    validate_required_fields(proxy)

    if node["tls_enabled"] or node["reality_enabled"]:
        proxy["tls"] = True
        proxy["servername"] = node.get("server_name") or server
        proxy["skip-cert-verify"] = node["skip_cert_verify"]

    if node["reality_enabled"]:
        proxy["client-fingerprint"] = node.get("fingerprint") or "chrome"
        proxy["reality-opts"] = clean_params(
            {
                "public-key": node.get("public_key"),
                "short-id": node.get("short_id"),
            }
        )

    network = transport_type(node)
    if network != "tcp":
        proxy["network"] = network

    if network == "ws":
        proxy["ws-opts"] = compact_options(
            {
                "path": node.get("path"),
            }
        )
        host = node.get("host")
        if host:
            proxy["ws-opts"]["headers"] = {"Host": host}

    if network == "http":
        proxy["http-opts"] = compact_options(
            {"path": [node.get("path")] if node.get("path") else None}
        )

    if network == "h2":
        proxy["h2-opts"] = compact_options(
            {
                "host": [node.get("host")] if node.get("host") else None,
                "path": node.get("path"),
            }
        )

    if network == "grpc":
        proxy["grpc-opts"] = compact_options({"grpc-service-name": node.get("service_name")})

    if network == "httpupgrade":
        proxy["http-upgrade-opts"] = compact_options(
            {
                "path": node.get("path"),
                "host": node.get("host"),
            }
        )

    return proxy


def validate_required_fields(proxy: dict) -> None:
    for key in ("server", "port", "type", "name"):
        if proxy.get(key) in (None, ""):
            raise ExportError(f"missing required clash field '{key}' in proxy {proxy}")

    if proxy["type"] in {"vmess", "vless", "tuic"} and not proxy.get("uuid"):
        raise ExportError(f"proxy '{proxy['name']}' is missing uuid")

    if proxy["type"] in {"trojan", "hysteria2", "tuic", "ss"} and not proxy.get("password"):
        raise ExportError(f"proxy '{proxy['name']}' is missing password")

    if proxy["type"] == "ss" and not proxy.get("cipher"):
        raise ExportError(f"proxy '{proxy['name']}' is missing cipher")


def build_config(proxies: list[dict]) -> dict:
    node_names = [proxy["name"] for proxy in proxies] or ["DIRECT"]
    return {
        "proxies": proxies,
        "proxy-groups": [
            {"name": "NODE", "type": "select", "proxies": node_names},
            {
                "name": "AUTO",
                "type": "url-test",
                "proxies": node_names,
                "url": "http://www.gstatic.com/generate_204",
                "interval": 300,
            },
            {"name": "FINAL", "type": "select", "proxies": ["NODE", "AUTO", "DIRECT"]},
        ],
        "rules": [
            "GEOIP,CN,DIRECT",
            "GEOSITE,CN,DIRECT",
            "MATCH,FINAL",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Export sing-box inbound configs as Clash config.")
    parser.add_argument("--conf-dir", default=DEFAULT_CONF_DIR, help="directory containing sing-box JSON files")
    parser.add_argument("--server", help="public server IP or domain used in exported nodes")
    parser.add_argument("--auto-ip", action="store_true", help="query a public IP service when --server is omitted")
    parser.add_argument("--output", default="./clash.yaml", help="output Clash file")
    parser.add_argument("--base64-output", help="optional file for base64-encoded config")
    args = parser.parse_args()

    nodes = load_nodes(args.conf_dir)
    proxies: list[dict] = []

    for node in nodes:
        try:
            server = resolve_server(node, args.server, args.auto_ip)
            proxy = build_proxy(node, server)
            if proxy:
                proxies.append(proxy)
        except Exception as e:
            print("foreach node error: {}".format(e))
    config = build_config(proxies)
    rendered = dump_yaml(config)

    output = Path(args.output)
    output.write_text(rendered, encoding="utf-8")
    print(f"wrote clash config to {output}")

    if args.base64_output:
        encoded = base64.b64encode(rendered.encode("utf-8")).decode("utf-8")
        base64_output = Path(args.base64_output)
        base64_output.write_text(encoded, encoding="utf-8")
        print(f"wrote base64 config to {base64_output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
