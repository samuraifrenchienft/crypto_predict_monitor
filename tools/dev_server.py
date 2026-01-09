import json
from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self._send_json({"status": "ok", "service": "dev_server"})
        elif self.path == "/events":
            self._send_json({
                "events": [
                    {
                        "id": "btc_up_1",
                        "title": "BTC above X",
                        "ts": "2026-01-01T00:00:00+00:00",
                        "p": 0.62,
                        "source": "dev",
                    },
                    {
                        "id": "eth_up_1",
                        "title": "ETH above Y",
                        "ts": "2026-01-01T00:00:10+00:00",
                        "p": 0.41,
                        "source": "dev",
                    },
                ]
            })
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/webhook":
            content_length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_length) if content_length > 0 else b""

            market_id = None
            severity = None

            try:
                payload = json.loads(body_bytes.decode("utf-8"))
                if isinstance(payload, dict):
                    alert = payload.get("alert")
                    if isinstance(alert, dict):
                        market_id = alert.get("market_id")
                        severity = alert.get("severity")
                    if not market_id:
                        market_id = payload.get("market_id")
                    if not severity:
                        severity = payload.get("severity")
            except Exception:
                pass

            print(f"WEBHOOK market_id={market_id} severity={severity}")

            self.send_response(204)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def _send_json(self, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        return


def main():
    server = HTTPServer(("127.0.0.1", 8089), Handler)
    print("dev server on http://127.0.0.1:8089")
    server.serve_forever()


if __name__ == "__main__":
    main()
