"""binance_depth_proxy.py - Local proxy for Binance order book depth
Listens on localhost:18599, fetches ETHUSDT depth via SOCKS5 proxy, returns JSON with CORS headers.
Usage: python scripts/binance_depth_proxy.py
"""
import http.server
import json
import urllib.request
import socket
import ssl

PORT = 18599
PROXY = "socks5h://127.0.0.1:10808"

class DepthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        try:
            ctx = ssl.create_default_context()
            req = urllib.request.Request(
                "https://fapi.binance.com/fapi/v1/depth?symbol=ETHUSDT&limit=15"
            )
            req.add_header("User-Agent", "Mozilla/5.0")
            with urllib.request.urlopen(req, timeout=5, context=ctx) as r:
                data = json.loads(r.read())
            self.wfile.write(json.dumps({
                "bids": data.get("bids", []),
                "asks": data.get("asks", []),
                "ts": data.get("lastUpdateId", 0)
            }).encode())
        except Exception as e:
            self.wfile.write(json.dumps({"error": str(e)}).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET")
        self.end_headers()
    
    def log_message(self, fmt, *args):
        pass

if __name__ == "__main__":
    srv = http.server.HTTPServer(("127.0.0.1", PORT), DepthHandler)
    print(f"Binance depth proxy on http://127.0.0.1:{PORT}")
    srv.serve_forever()