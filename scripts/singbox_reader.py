from __future__ import annotations

import base64
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

DEFAULT_CONF_DIR = "/etc/sing-box/conf"
PUBLIC_IP_ENDPOINTS = (
    "https://api.ipify.org",
    "https://ifconfig.me/ip",
)


class ExportError(RuntimeError):
    pass


def load_nodes(conf_dir: str) -> list[dict[str, Any]]:
    conf_path = Path(conf_dir)
    if not conf_path.exists():
        raise ExportError(f"config directory not found: {conf_path}")

    nodes: list[dict[str, Any]] = []
    for path in sorted(conf_path.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        inbounds = data.get("inbounds") or []
        if not inbounds:
            continue
        nodes.append(normalize_node(path, inbounds[0]))

    if not nodes:
        raise ExportError(f"no json configs found in: {conf_path}")

    return nodes


def normalize_node(path: Path, inbound: dict[str, Any]) -> dict[str, Any]:
    users = inbound.get("users") or [{}]
    user = users[0] if users else {}
    tls = inbound.get("tls") or {}
    reality = tls.get("reality") or {}
    transport = inbound.get("transport") or {}
    headers = transport.get("headers") or {}
    utls = tls.get("utls") or {}
    obfs = inbound.get("obfs") or {}
    alpn = tls.get("alpn") or []

    return {
        "name": path.stem,
        "protocol": inbound.get("type"),
        "port": inbound.get("listen_port"),
        "listen": inbound.get("listen"),
        "server_name": tls.get("server_name"),
        "tls_enabled": bool(tls.get("enabled")),
        "skip_cert_verify": bool(
            tls.get("insecure") or tls.get("skip_cert_verify") or tls.get("skip-cert-verify")
        ),
        "reality_enabled": bool(reality),
        "public_key": reality.get("public_key"),
        "short_id": reality.get("short_id") or reality.get("short-id"),
        "fingerprint": utls.get("fingerprint"),
        "network": transport.get("type") or "tcp",
        "path": transport.get("path") or "",
        "host": transport.get("host") or headers.get("Host") or headers.get("host"),
        "service_name": transport.get("service_name") or transport.get("serviceName"),
        "method": inbound.get("method"),
        "uuid": user.get("uuid"),
        "password": user.get("password"),
        "username": user.get("username"),
        "flow": user.get("flow"),
        "congestion_control": inbound.get("congestion_control"),
        "udp_relay_mode": inbound.get("udp_relay_mode"),
        "zero_rtt_handshake": inbound.get("zero_rtt_handshake"),
        "obfs_type": obfs.get("type"),
        "obfs_password": obfs.get("password"),
        "alpn": [str(item) for item in alpn] if isinstance(alpn, list) else [str(alpn)],
        "raw": inbound,
    }


def resolve_server(node: dict[str, Any], server: str | None, auto_ip: bool) -> str:
    if server:
        return server

    if node.get("server_name"):
        return str(node["server_name"])

    listen = node.get("listen")
    if listen and listen not in ("::", "::1", "0.0.0.0", "127.0.0.1"):
        return str(listen)

    if auto_ip:
        ip = discover_public_ip()
        if ip:
            return ip

    raise ExportError(
        f"unable to determine public server for node '{node['name']}'. "
        "Pass --server or use --auto-ip."
    )


def discover_public_ip() -> str | None:
    for endpoint in PUBLIC_IP_ENDPOINTS:
        try:
            request = Request(endpoint, headers={"User-Agent": "codex-sing-box-exporter"})
            with urlopen(request, timeout=4) as response:
                value = response.read().decode("utf-8").strip()
            if value:
                return value
        except Exception:
            continue
    return None


def clean_params(params: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in params.items():
        if value is None:
            continue
        if value == "":
            continue
        if value is False:
            continue
        if isinstance(value, list):
            if not value:
                continue
            result[key] = ",".join(str(item) for item in value)
            continue
        result[key] = str(value)
    return result


def encode_query(params: dict[str, Any]) -> str:
    cleaned = clean_params(params)
    return urlencode(cleaned, quote_via=quote)


def encode_name(value: str) -> str:
    return quote(value, safe="")


def b64_plain(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("utf-8")


def b64_url(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode("utf-8")).decode("utf-8").rstrip("=")


def protocol_security(node: dict[str, Any]) -> str:
    if node["reality_enabled"]:
        return "reality"
    if node["tls_enabled"]:
        return "tls"
    return "none"


def transport_type(node: dict[str, Any]) -> str:
    return str(node.get("network") or "tcp")


def warning(message: str) -> None:
    print(f"warning: {message}", file=sys.stderr)


def minimal_yaml_dump(value: Any, indent: int = 0) -> str:
    if isinstance(value, dict):
        lines: list[str] = []
        for key, item in value.items():
            prefix = " " * indent + f"{key}:"
            if isinstance(item, (dict, list)):
                lines.append(prefix)
                lines.append(minimal_yaml_dump(item, indent + 2))
            else:
                lines.append(prefix + f" {format_yaml_scalar(item)}")
        return "\n".join(lines)

    if isinstance(value, list):
        lines = []
        for item in value:
            prefix = " " * indent + "-"
            if isinstance(item, (dict, list)):
                lines.append(prefix)
                lines.append(minimal_yaml_dump(item, indent + 2))
            else:
                lines.append(prefix + f" {format_yaml_scalar(item)}")
        return "\n".join(lines)

    return " " * indent + format_yaml_scalar(value)


def format_yaml_scalar(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)

    text = str(value)
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def dump_yaml(value: Any) -> str:
    try:
        import yaml  # type: ignore

        return yaml.safe_dump(value, allow_unicode=True, sort_keys=False)
    except Exception:
        return minimal_yaml_dump(value) + "\n"
