import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import issueloop


class _Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, payload: dict):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        repo = params.get("repo", [None])[0]

        if parsed.path == "/health":
            self._send(200, {"status": "ok"})
        elif parsed.path == "/errors/top":
            ticket = issueloop.get_top_error(repo)
            self._send(200, ticket or {})
        elif parsed.path == "/errors/all":
            self._send(200, {"tickets": issueloop.get_all_errors(repo)})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            data = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._send(400, {"error": "invalid JSON body"})
            return

        if self.path == "/errors/resolve" and "id" in data:
            issueloop.resolve(data["id"])
            self._send(200, {"status": "resolved"})
        elif self.path == "/errors/fail" and "id" in data:
            issueloop.fail(data["id"])
            self._send(200, {"status": "failed"})
        else:
            self._send(400, {"error": "expected JSON body with an 'id' field"})

    def log_message(self, format, *args):
        pass


def serve(port: int = 8787):
    server = HTTPServer(("127.0.0.1", port), _Handler)
    print(f"issueloop serving on http://127.0.0.1:{port}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")