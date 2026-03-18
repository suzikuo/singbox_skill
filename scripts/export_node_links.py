from __future__ import annotations

import argparse
import json
from pathlib import Path

from singbox_reader import (
    DEFAULT_CONF_DIR,
    ExportError,
    b64_plain,
    b64_url,
    clean_params,
    encode_name,
    encode_query,
    load_nodes,
    protocol_security,
    resolve_server,
    transport_type,
    warning,
)


def build_link(node: dict, server: str) -> str | None:
    protocol = node["protocol"]
    port = node["port"]
    name = encode_name(node["name"])
    network = transport_type(node)

    if protocol == "vmess":
        if not node.get("uuid"):
            raise ExportError(f"vmess node '{node['name']}' is missing users[0].uuid")
        payload = {
            "v": "2",
            "ps": node["name"],
            "add": server,
            "port": str(port),
            "id": node["uuid"],
            "aid": "0",
            "scy": "auto",
            "net": network,
            "type": "none",
            "host": node.get("host") or "",
            "path": node.get("path") or "",
            "tls": "tls" if node["tls_enabled"] else "",
            "sni": node.get("server_name") or "",
            "alpn": ",".join(node.get("alpn") or []),
        }
        return "vmess://" + b64_plain(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))

    if protocol == "vless":
        if not node.get("uuid"):
            raise ExportError(f"vless node '{node['name']}' is missing users[0].uuid")
        params = clean_params(
            {
                "encryption": "none",
                "security": protocol_security(node),
                "type": network,
                "sni": node.get("server_name"),
                "host": node.get("host"),
                "path": node.get("path"),
                "serviceName": node.get("service_name"),
                "flow": node.get("flow"),
                "pbk": node.get("public_key"),
                "sid": node.get("short_id"),
                "fp": node.get("fingerprint"),
                "alpn": node.get("alpn"),
            }
        )
        return f"vless://{node['uuid']}@{server}:{port}?{encode_query(params)}#{name}"

    if protocol == "trojan":
        if not node.get("password"):
            raise ExportError(f"trojan node '{node['name']}' is missing users[0].password")
        params = clean_params(
            {
                "security": protocol_security(node),
                "type": network,
                "sni": node.get("server_name"),
                "host": node.get("host"),
                "path": node.get("path"),
                "serviceName": node.get("service_name"),
                "pbk": node.get("public_key"),
                "sid": node.get("short_id"),
                "fp": node.get("fingerprint"),
                "alpn": node.get("alpn"),
            }
        )
        password = encode_name(str(node["password"]))
        return f"trojan://{password}@{server}:{port}?{encode_query(params)}#{name}"

    if protocol == "hysteria2":
        if not node.get("password"):
            raise ExportError(f"hysteria2 node '{node['name']}' is missing users[0].password")
        params = clean_params(
            {
                "sni": node.get("server_name"),
                "insecure": 1 if node["skip_cert_verify"] else None,
                "obfs": node.get("obfs_type"),
                "obfs-password": node.get("obfs_password"),
            }
        )
        query = encode_query(params)
        suffix = f"?{query}" if query else ""
        password = encode_name(str(node["password"]))
        return f"hysteria2://{password}@{server}:{port}{suffix}#{name}"

    if protocol == "tuic":
        if not node.get("uuid") or not node.get("password"):
            raise ExportError(f"tuic node '{node['name']}' is missing uuid or password")
        params = clean_params(
            {
                "congestion_control": node.get("congestion_control"),
                "udp_relay_mode": node.get("udp_relay_mode"),
                "sni": node.get("server_name"),
                "alpn": node.get("alpn"),
                "allow_insecure": 1 if node["skip_cert_verify"] else None,
            }
        )
        query = encode_query(params)
        suffix = f"?{query}" if query else ""
        password = encode_name(str(node["password"]))
        return f"tuic://{node['uuid']}:{password}@{server}:{port}{suffix}#{name}"

    if protocol == "shadowsocks":
        if not node.get("method") or not node.get("password"):
            raise ExportError(f"shadowsocks node '{node['name']}' is missing method or password")
        userinfo = b64_url(f"{node['method']}:{node['password']}")
        return f"ss://{userinfo}@{server}:{port}#{name}"

    if protocol == "socks":
        username = node.get("username")
        password = node.get("password")
        if username and password:
            username = encode_name(str(username))
            password = encode_name(str(password))
            return f"socks5://{username}:{password}@{server}:{port}#{name}"
        return f"socks5://{server}:{port}#{name}"

    warning(f"share link export does not support protocol '{protocol}' for node '{node['name']}'")
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Export sing-box inbound configs as share links.")
    parser.add_argument("--conf-dir", default=DEFAULT_CONF_DIR, help="directory containing sing-box JSON files")
    parser.add_argument("--server", help="public server IP or domain used in exported links")
    parser.add_argument("--auto-ip", action="store_true", help="query a public IP service when --server is omitted")
    parser.add_argument("--output", default="./node.txt", help="output file path")
    args = parser.parse_args()

    nodes = load_nodes(args.conf_dir)
    lines: list[str] = []

    for node in nodes:
        server = resolve_server(node, args.server, args.auto_ip)
        link = build_link(node, server)
        if link:
            lines.append(link)

    output = Path(args.output)
    output.write_text("\n".join(dict.fromkeys(lines)) + ("\n" if lines else ""), encoding="utf-8")
    print(f"exported {len(lines)} links to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
