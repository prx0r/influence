#!/usr/bin/env python3
"""fable-mcp-stdio: MCP stdio bridge -> influence dash /mcp (the studio backend).

Usage (opencode / Claude Code MCP config, type stdio):
  {"command": "python3",
   "args": ["/root/influence2/dash/fable-mcp-stdio.py"],
   "env": {"DASH_PORT": "8795", "DASH_TOKEN": "<dash token if set>"}}

Speaks JSON-RPC over stdio (initialize, tools/list, tools/call);
forwards to POST 127.0.0.1:<port>/mcp {method, params}.
All writes stay behind the dash's own gates (drafts; publish human-gated).
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request

PORT = os.environ.get("DASH_PORT", "8795")
TOKEN = os.environ.get("DASH_TOKEN", "")
BASE = f"http://127.0.0.1:{PORT}/mcp" + (f"?token={TOKEN}" if TOKEN else "")


def call_dash(method: str, params: dict) -> dict:
    body = json.dumps({"method": method, "params": params}).encode()
    req = urllib.request.Request(BASE, data=body,
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read() or b"{}")


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            sys.stdout.write(json.dumps(
                {"jsonrpc": "2.0", "id": None,
                 "error": {"code": -32700, "message": "parse error"}}) + "\n")
            sys.stdout.flush()
            continue
        mid, method, params = msg.get("id"), msg.get("method"), msg.get("params") or {}
        if method == "initialize":
            res = {"protocolVersion": "2024-11-05",
                   "capabilities": {"tools": {}},
                   "serverInfo": {"name": "fable-studio", "version": "1.0.0"}}
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": mid, "result": res}) + "\n")
        elif method in ("notifications/initialized", "notifications/cancelled"):
            continue
        elif method == "tools/list":
            dash = call_dash("tools/list", {})
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": mid,
                                         "result": {"tools": dash.get("tools", [])}}) + "\n")
        elif method == "tools/call":
            dash = call_dash("tools/call", params)
            if "error" in dash:
                sys.stdout.write(json.dumps(
                    {"jsonrpc": "2.0", "id": mid,
                     "error": {"code": -32000, "message": str(dash["error"])}}) + "\n")
            else:
                sys.stdout.write(json.dumps(
                    {"jsonrpc": "2.0", "id": mid,
                     "result": {"content": [{"type": "text",
                                            "text": json.dumps(dash.get("result"))}]}}) + "\n")
        else:
            sys.stdout.write(json.dumps(
                {"jsonrpc": "2.0", "id": mid,
                 "error": {"code": -32601, "message": "unknown method"}}) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
