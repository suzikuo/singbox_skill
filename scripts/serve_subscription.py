import argparse
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from export_clash import build_config, build_proxy
from export_node_links import build_link
from singbox_reader import (
    DEFAULT_CONF_DIR,
    b64_plain,
    discover_public_ip,
    dump_yaml,
    load_nodes,
    resolve_server,
)


class SubscriptionHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/sabusuku":
            self.send_error(404, "Not Found")
            return

        query = parse_qs(parsed.query)
        token = query.get("token", [""])[0]

        if self.server.token and token != self.server.token:
            self.send_error(401, "Unauthorized")
            return

        try:
            fmt = query.get("format", [""])[0].lower()
            user_agent = self.headers.get("User-Agent", "").lower()
            is_clash = fmt == "clash" or "clash" in user_agent or "meta" in user_agent

            nodes = load_nodes(self.server.conf_dir)
            
            if is_clash:
                proxies = []
                for node in nodes:
                    try:
                        server_ip_or_domain = resolve_server(
                            node, self.server.public_server, self.server.auto_ip
                        )
                        proxy = build_proxy(node, server_ip_or_domain)
                        if proxy:
                            proxies.append(proxy)
                    except Exception as e:
                        print(
                            f"Warning: skipping node '{node.get('name', 'unknown')}': {e}",
                            file=sys.stderr,
                        )
                config = build_config(proxies)
                content = dump_yaml(config)
                response_data = content.encode("utf-8")
                content_type = "text/yaml; charset=utf-8"
            else:
                lines = []
                for node in nodes:
                    try:
                        server_ip_or_domain = resolve_server(
                            node, self.server.public_server, self.server.auto_ip
                        )
                        link = build_link(node, server_ip_or_domain)
                        if link:
                            lines.append(link)
                    except Exception as e:
                        print(
                            f"Warning: skipping node '{node.get('name', 'unknown')}': {e}",
                            file=sys.stderr,
                        )
    
                content = "\n".join(dict.fromkeys(lines)) + ("\n" if lines else "")
                response_data = b64_plain(content).encode("utf-8")
                content_type = "text/plain; charset=utf-8"

            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(response_data)))
            self.end_headers()
            self.wfile.write(response_data)
        except Exception as e:
            self.send_error(500, f"Internal Server Error: {e}")


class SubscriptionServer(HTTPServer):
    def __init__(
        self,
        server_address,
        RequestHandlerClass,
        conf_dir,
        token,
        public_server,
        auto_ip,
    ):
        self.conf_dir = conf_dir
        self.token = token
        self.public_server = public_server
        self.auto_ip = auto_ip
        super().__init__(server_address, RequestHandlerClass)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Serve sing-box inbound configs as a subscription link."
    )
    parser.add_argument(
        "--conf-dir",
        default=DEFAULT_CONF_DIR,
        help="directory containing sing-box JSON files",
    )
    parser.add_argument(
        "--host", default="0.0.0.0", help="host to listen on (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=8080, help="port to listen on (default: 8080)"
    )
    parser.add_argument(
        "--token", required=True, help="token required for the /sabusuku endpoint"
    )
    parser.add_argument(
        "-f", "--foreground", action="store_true", help="run server in foreground"
    )

    args = parser.parse_args()

    print("Auto-detecting public IP...")
    public_server = discover_public_ip()
    if not public_server:
        print(
            "Warning: Could not detect public IP. Links might use internal or missing IPs.",
            file=sys.stderr,
        )

    domain = public_server if public_server else args.host
    url = f"http://{domain}:{args.port}/sabusuku?token={args.token}"

    if not args.foreground:
        # Run in background
        import subprocess

        cmd_args = [sys.executable, sys.argv[0], "--foreground"]
        cmd_args.extend(arg for arg in sys.argv[1:] if arg not in ("-f", "--foreground"))

        if sys.platform == "win32":
            CREATE_NO_WINDOW = 0x08000000
            subprocess.Popen(cmd_args, creationflags=CREATE_NO_WINDOW)
        else:
            subprocess.Popen(
                cmd_args,
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        print("Subscription server started in background.")
        print(f"URL: {url}")
        print(f"Clash: {url}&format=clash")
        return 0

    server = SubscriptionServer(
        (args.host, args.port),
        SubscriptionHandler,
        args.conf_dir,
        args.token,
        public_server,
        True,  # auto_ip enabled by default as fallback inside resolve_server
    )

    print(f"Starting subscription server on {url}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.server_close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
