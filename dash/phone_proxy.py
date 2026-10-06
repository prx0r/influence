#!/usr/bin/env python3
"""Phone edge proxy — phone.agentcom.org → oddhobb-phone worker.
Stdlib only. Free inbound + agent reads. Never spends."""
from __future__ import annotations
import json, os, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

UP = os.environ.get("PHONE_UPSTREAM", "https://oddhobb-phone.tradesprior.workers.dev").rstrip("/")
PORT = int(os.environ.get("PHONE_PROXY_PORT", "8794"))
AUTH = ""
auth_file = os.environ.get("PHONE_AUTH_FILE", "/root/stevejobless/.phone_auth")
if os.path.exists(auth_file):
    AUTH = open(auth_file).read().strip()

class H(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type,Authorization")
    def log_message(self, fmt, *args):
        print("[phone-proxy]", fmt % args)
    def do_OPTIONS(self):
        self.send_response(204); self._cors(); self.end_headers()
    def _proxy(self, method):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        headers = {"Content-Type": self.headers.get("Content-Type") or "application/json",
                   "User-Agent": "phone-agentcom-proxy/0.1"}
        # This edge is the owner's UI: always use the server-side key for gated
        # paths. Client-supplied keys are ignored (a stale oh_phone_key in
        # localStorage used to 401 the UI). Direct worker access stays gated.
        gated = (parsed.path.startswith("/v1/") and not parsed.path.startswith("/v1/telnyx/") and not parsed.path.startswith("/v1/health") and not parsed.path.startswith("/v1/status"))
        if AUTH and gated:
            headers["Authorization"] = f"Bearer {AUTH}"
        req = urllib.request.Request(UP + parsed.path + (f"?{parsed.query}" if parsed.query else ""),
                                     data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = resp.read()
                self.send_response(resp.status)
                self.send_header("Content-Type", resp.headers.get("Content-Type") or "application/json")
                self._cors(); self.end_headers(); self.wfile.write(data)
        except urllib.error.HTTPError as e:
            data = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", "application/json"); self._cors(); self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            msg = json.dumps({"error": str(e)[:200], "upstream": UP}).encode()
            self.send_response(502); self.send_header("Content-Type","application/json"); self._cors(); self.end_headers()
            self.wfile.write(msg)
    def do_GET(self): self._proxy("GET")
    def do_POST(self): self._proxy("POST")

if __name__ == "__main__":
    print(f"phone proxy {PORT} -> {UP}")
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
