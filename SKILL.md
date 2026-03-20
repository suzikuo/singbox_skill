---
name: sing-box-ops
description: Inspect, explain, repair, and export sing-box server configurations, especially 233boy-style deployments that store inbound JSON files under /etc/sing-box/conf. Use when Codex needs to read sing-box config files, map protocol fields, generate share links, export Clash or Clash Meta subscriptions, troubleshoot TLS or REALITY transport settings, or document how a sing-box node should be consumed by clients.some scripts in ./scripts/
---

# Sing-box workflow

> **AVAILABLE SCRIPTS (USE THESE FIRST instead of rewriting exporters)**:
>  **CRITICAL PATH INSTRUCTION**: These scripts are located in the `scripts/` directory relative to this `SKILL.md` file. Because your working directory may be different, you **MUST use their absolute paths** (or `cd` into this skill's directory) when executing them!
> - `scripts/export_node_links.py`: Export sing-box nodes as standard v2ray-style links.
> - `scripts/export_clash.py`: Export sing-box nodes as a Clash/Meta YAML profile.
> - `scripts/serve_subscription.py`: Run an HTTP server to provide live subscription URLs. Supports both standard V2Ray links (default) and Clash/Meta profiles (`?format=clash` or via Clash User-Agent).and return dict:{"url": url, "clash": f"{url}&format=clash"}

Treat each `*.json` file in `/etc/sing-box/conf` as one inbound node unless the user shows a different layout.

Start by listing config files and reading one or two representative JSON files before editing or exporting anything. Do not assume every node uses the same protocol, transport, TLS mode, or user schema.

## Preferred scripts

Use the bundled scripts instead of rewriting exporters:

- Share links: `python /absolute/path/to/skill/scripts/export_node_links.py --conf-dir /etc/sing-box/conf --server example.com --output ./node.txt`
- Clash config: `python /absolute/path/to/skill/scripts/export_clash.py --conf-dir /etc/sing-box/conf --server example.com --output ./clash.yaml --base64-output ./clash_base64.txt`
- Subscription server: `python /absolute/path/to/skill/scripts/serve_subscription.py --token <TOKEN> --port 8080` (Auto-detects IP. Link: `http://<IP>:8080/sabusuku?token=<TOKEN>` or append `&format=clash` for Clash profiles)

Pass `--server` whenever the JSON files do not already imply the public endpoint. If `tls.server_name` is present, the scripts use it as a fallback. Add `--auto-ip` only when an external IP lookup is acceptable.

## Working rules

Verify the first inbound object before exporting:

- Read `inbounds[0].type`, `listen_port`, `users[0]`, `transport`, and `tls`.
- Check whether the node is plain TLS, REALITY, or no TLS.
- Check whether the transport is `tcp`, `ws`, `http`, `h2`, `grpc`, or `httpupgrade`.

Prefer explicit failure or warnings over silent field loss. If a protocol or field is unsupported by the destination format, report it.

## Resource map

- Protocol and field mapping notes: `references/protocol-mapping.md`
- Shared parser helpers: `scripts/singbox_reader.py`
- Share-link exporter: `scripts/export_node_links.py`
- Clash exporter: `scripts/export_clash.py`
- Subscription server: `scripts/serve_subscription.py`

## Troubleshooting

If export results look wrong:

- Re-check whether the public endpoint should be a domain, not the server IP.
- Re-check `tls.server_name`, REALITY public key, short ID, and transport path or host headers.
- Re-check whether the destination client actually supports that protocol and transport combination.
