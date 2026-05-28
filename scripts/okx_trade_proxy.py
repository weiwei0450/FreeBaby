#!/usr/bin/env python3
"""OKX Trade Proxy - Demo Trading (Auto + Data Display)"""
import http.server, json, urllib.request, urllib.error, ssl, hmac, hashlib, base64, datetime, sys

sys.path.insert(0, r"F:\FreeBaby-main")
import mykey

cfg = mykey.okx_config
API_KEY = cfg['api_key']
SECRET_KEY = cfg['secret_key']
PASSPHRASE = cfg['passphrase']
DEMO = cfg.get('demo_trading', True)
PORT = 18600

def ts():
    now = datetime.datetime.now(datetime.timezone.utc)
    return now.strftime('%Y-%m-%dT%H:%M:%S.') + f"{now.microsecond // 1000:03d}Z"

def sign(t, method, path, body=''):
    msg = t + method + path + body
    return base64.b64encode(hmac.new(SECRET_KEY.encode(), msg.encode(), hashlib.sha256).digest()).decode()

def okx_req(method, path, body=None):
    url = f"https://www.okx.com{path}"
    body_str = json.dumps(body) if body else ''
    t = ts()
    sig = sign(t, method, path, body_str)
    req = urllib.request.Request(url, data=body_str.encode() if body_str else None, method=method)
    req.add_header('OK-ACCESS-KEY', API_KEY)
    req.add_header('OK-ACCESS-SIGN', sig)
    req.add_header('OK-ACCESS-TIMESTAMP', t)
    req.add_header('OK-ACCESS-PASSPHRASE', PASSPHRASE)
    req.add_header('Content-Type', 'application/json')
    if DEMO:
        req.add_header('x-simulated-trading', '1')
    try:
        with urllib.request.urlopen(req, timeout=10, context=ssl.create_default_context()) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {'error': f'HTTP {e.code}', 'body': e.read().decode()[:200]}
    except Exception as e:
        return {'error': str(e)}

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path
        if path == '/positions':
            resp = okx_req('GET', '/api/v5/account/positions?instType=SWAP')
        elif path == '/orders':
            resp = okx_req('GET', '/api/v5/trade/orders-pending?instType=SWAP')
        elif path == '/balance':
            resp = okx_req('GET', '/api/v5/account/balance')
        else:
            resp = {'error': 'unknown endpoint'}
        self.send_response(200)
        self._cors()
        self.end_headers()
        self.wfile.write(json.dumps(resp).encode())

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        if not length:
            self.send_response(400); self._cors(); self.end_headers()
            self.wfile.write(b'{"error":"no body"}'); return
        try:
            data = json.loads(self.rfile.read(length))
        except:
            self.send_response(400); self._cors(); self.end_headers()
            self.wfile.write(b'{"error":"bad json"}'); return
        resp = okx_req('POST', '/api/v5/trade/order', data)
        self.send_response(200); self._cors(); self.end_headers()
        self.wfile.write(json.dumps(resp).encode())

    def do_OPTIONS(self):
        self.send_response(200); self._cors(); self.end_headers()

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def log_message(self, *a): pass

if __name__ == '__main__':
    s = http.server.HTTPServer(('127.0.0.1', PORT), H)
    print(f'OKX Trade Proxy on :{PORT} demo={DEMO}')
    s.serve_forever()
