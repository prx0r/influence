#!/usr/bin/env python3
"""Call the influence MCP from qpbot workers, Pi extensions, or shell.
Reads the dash token from dash/.token (same box). Never prints the token.

Usage:
  mcp-call.py tools/list
  mcp-call.py tools/call influencer.list '{}'
  mcp-call.py tools/call queue.list '{}'
  mcp-call.py tools/call graph.describe '{}'
"""
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_FILE = os.path.join(ROOT, "dash", ".token")
BASE = os.environ.get("INFLUENCE_DASH", "http://127.0.0.1:8793")


def call(method, name=None, arguments=None):
    with open(TOKEN_FILE) as f:
        token = f.read().strip()
    body = {"method": method, "params": {}}
    if name:
        body["params"] = {"name": name, "arguments": arguments or {}}
    req = urllib.request.Request(
        f"{BASE}/mcp?token={token}", data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("tools/list", "tools/call"):
        print(__doc__.strip())
        raise SystemExit(2)
    if sys.argv[1] == "tools/list":
        print(json.dumps(call("tools/list"), indent=1))
    else:
        print(json.dumps(call("tools/call", sys.argv[2],
                              json.loads(sys.argv[3] if len(sys.argv) > 3 else "{}")),
                         indent=1))
