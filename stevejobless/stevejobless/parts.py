"""Parts lookup — MCP-catalog pattern, MIT-inspired (whatsapp-shopify-agent).

Any supplier with a queryable endpoint (MCP or plain JSON HTTP) becomes live
stock+price instead of a stub table. Set PARTS_MCP_URL to enable; otherwise
static fallback table. Never blocks quoting: failures degrade to tbd lines.
"""
from __future__ import annotations

import json
import os
from typing import Any
from urllib.request import Request, urlopen

FALLBACK_PRICES = {  # GBP estimates, always quoted as estimates
    "32A RCBO": 45.0, "SWA cable (per m)": 6.5, "mounting kit": 25.0,
    "10-way dual-RCD board": 120.0, "RCBOs": 38.0, "labels/cert": 15.0,
}


def lookup(part: str, timeout: float = 5.0) -> dict[str, Any]:
    """Return {price|None, stock|None, url|None, live: bool}."""
    url = os.getenv("PARTS_MCP_URL", "")
    if url:
        try:
            req = Request(url, data=json.dumps({"q": part}).encode(),
                          headers={"Content-Type": "application/json"}, method="POST")
            with urlopen(req, timeout=timeout) as resp:
                d = json.loads(resp.read())
                return {"price": d.get("price"), "stock": d.get("stock"),
                        "url": d.get("url"), "live": True}
        except Exception:
            pass
    return {"price": FALLBACK_PRICES.get(part), "stock": None, "url": None, "live": False}
