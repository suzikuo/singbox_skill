import argparse
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from singbox_reader import DEFAULT_CONF_DIR, b64_plain, load_nodes, resolve_server
from export_node_links import build_link

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
            nodes = load_nodes(self.server.conf_dir)
            lines = []
            for node in nodes:
                try:
                    server_ip_or_domain = resolve_server(node, self.server.public_server, self.server.auto_ip)
                    link = build_link(node, server_ip_or_domain)
                    if link:
                        lines.append(link)
                except Exception as e:
                    print(f"Warning: skipping node '{node.get('name', 'unknown')}': {e}", file=sys.stderr)
            
            content = "\n".join(dict.fromkeys(lines)) + ("\n" if lines else "")
            base64_content = b64_plain(content)

            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(base64_content)))
            self.end_headers()
            self.wfile.write(base64_content.encode("utf-8"))
        except Exception as e:
            self.send_error(500, f"Internal Server Error: {e}")

class SubscriptionServer(HTTPServer):
    def __init__(self, server_address, RequestHandlerClass, conf_dir, token, public_server, auto_ip):
        self.conf_dir = conf_dir
        self.token = token
        self.public_server = public_server
        self.auto_ip = auto_ip
        super().__init__(server_address, RequestHandlerClass)

def main() -> int:
    parser = argparse.ArgumentParser(description="Serve sing-box inbound configs as a subscription link.")
    parser.add_argument("--conf-dir", default=DEFAULT_CONF_DIR, help="directory containing sing-box JSON files")
    parser.add_argument("--server", help="public server IP or domain used in exported links")
    parser.add_argument("--auto-ip", action="store_true", help="query a public IP service when --server is omitted")
    parser.add_argument("--host", default="0.0.0.0", help="host to listen on (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8080, help="port to listen on (default: 8080)")
    parser.add_argument("--token", required=True, help="token required for the /sabusuku endpoint")
    
    args = parser.parse_args()

    server = SubscriptionServer(
        (args.host, args.port),
        SubscriptionHandler,
        args.conf_dir,
        args.token,
        args.server,
        args.auto_ip
    )

    url = f"http://{args.host}:{args.port}/sabusuku?token={args.token}"
    print(f"Starting subscription server on {url}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.server_close()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
