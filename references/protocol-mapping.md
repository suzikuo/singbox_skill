# Protocol Mapping

Use this file when the target format or client capability is unclear.

## Config assumptions

- Each JSON file under `/etc/sing-box/conf` is treated as one inbound node.
- The exporters currently read `inbounds[0]` only.
- Public endpoint resolution order is: `--server`, `tls.server_name`, non-wildcard `listen`, then `--auto-ip`.

## Share-link notes

- `vmess` links must use a base64-encoded JSON payload, not `vmess://uuid@host:port`.
- `vless` and `trojan` links need correct `security`, `type`, `sni`, and transport fields or clients will fail silently.
- REALITY exports need `pbk`, and usually `sid` and `fp`.
- `tuic`, `hysteria2`, and `shadowsocks` links are exported only when the required auth fields are present.

## Clash notes

- Output is aimed at Clash Meta compatible syntax for modern protocols such as `vless`, `tuic`, and `hysteria2`.
- Unsupported protocols are skipped with a warning instead of being emitted incorrectly.
- Transport-specific blocks are emitted only when the corresponding fields exist.

## Safe workflow

1. Inspect a real config file before exporting.
2. Confirm the intended public endpoint.
3. Export.
4. Re-open one output entry and verify port, transport, TLS mode, and auth field.
