"""Fish Audio MCP provider — server-side client for the dash/pi studio.

Reads/writes its own token file (NOT opencode's mcp-auth.json — independent
OAuth session, no cross-writer fights). Seeded once from opencode's file;
refreshes independently via the public-client refresh_grant (auth method
none, same as the CLI flow).

RULE 1: nothing here spends on its own. Free reads (balance, voices search,
estimates) run direct. Anything that burns package credits (text_to_speech,
studio_generate/export, generate_image/video) is ONLY invoked through
pipeline.runtime.execute with a verified grant — see pipeline/audio_flow.py.
Direct calls to the `speak`/`generate` helpers fail closed without ctx grant.
"""
from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request

MCP_URL = "https://api.fish.audio/mcp"
TOKEN_URL = "https://api.fish.audio/oauth/token"
PROTOCOL = "2025-06-18"

TOKEN_PATH = os.path.join(os.path.expanduser("~"), ".config", "influence",
                           "fish-mcp.json")
SEED_PATH = os.path.join(os.path.expanduser("~"), ".local", "share",
                         "opencode", "mcp-auth.json")


def _load_tokens() -> dict:
    """Load our token file; seed from opencode's on first run."""
    if os.path.isfile(TOKEN_PATH):
        with open(TOKEN_PATH, encoding="utf-8") as f:
            return json.load(f)
    if os.path.isfile(SEED_PATH):
        with open(SEED_PATH, encoding="utf-8") as f:
            seed = json.load(f).get("fish-audio", {})
        toks = {"tokens": seed.get("tokens", {}),
                "clientInfo": seed.get("clientInfo", {})}
        _save_tokens(toks)
        return toks
    raise SystemExit("fish provider: no tokens — run `opencode mcp auth fish-audio` "
                     "once, then retry (provider seeds from it)")


def _save_tokens(toks: dict) -> None:
    os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
    tmp = TOKEN_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(toks, f)
    os.chmod(tmp, 0o600)
    os.replace(tmp, TOKEN_PATH)


def _refresh(toks: dict) -> dict:
    """Refresh access token. Public client, no secret."""
    refresh = (toks.get("tokens") or {}).get("refreshToken", "")
    client_id = (toks.get("clientInfo") or {}).get("clientId", "")
    if not refresh or not client_id:
        raise SystemExit("fish provider: no refresh token — re-auth via opencode")
    params = {"grant_type": "refresh_token", "refresh_token": refresh,
              "client_id": client_id}
    req = urllib.request.Request(
        TOKEN_URL, data=urllib.parse.urlencode(params).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        new = json.load(r)
    merged = dict(toks.get("tokens") or {})
    merged.update({"accessToken": new["access_token"]})
    if new.get("refresh_token"):
        merged["refreshToken"] = new["refresh_token"]
    if new.get("expires_in"):
        merged["expiresAt"] = int(time.time() * 1000) + int(new["expires_in"]) * 1000
    toks["tokens"] = merged
    _save_tokens(toks)
    return toks


def _token() -> str:
    toks = _load_tokens()
    t = toks.get("tokens") or {}
    if t.get("expiresAt", 0) and t["expiresAt"] < int(time.time() * 1000) + 60000:
        toks = _refresh(toks)
        t = toks["tokens"]
    return t.get("accessToken", "")


def _headers(session: str | None = None) -> dict:
    h = {"Authorization": f"Bearer {_token()}",
         "Content-Type": "application/json",
         "Accept": "application/json, text/event-stream",
         "MCP-Protocol-Version": PROTOCOL}
    if session:
        h["Mcp-Session-Id"] = session
    return h


def _post(obj: dict, session: str | None = None) -> tuple[str | None, str]:
    req = urllib.request.Request(MCP_URL, data=json.dumps(obj).encode(),
                                 headers=_headers(session))
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.headers.get("Mcp-Session-Id"), r.read().decode()


def _parse(raw: str, mid: int) -> dict:
    raw = raw.strip()
    if raw.startswith("{"):
        return json.loads(raw)
    for line in raw.splitlines():
        if line.startswith("data:"):
            try:
                m = json.loads(line[5:])
                if m.get("id") == mid:
                    return m
            except Exception:
                continue
    raise RuntimeError(f"fish mcp: no result for id={mid}: {raw[:200]}")


def call_tool(name: str, args: dict | None = None) -> dict:
    """Call one Fish MCP tool. Free reads return data; billed tools return
    the server result (caller = audio_flow via runtime.execute + grant)."""
    sid, _ = _post({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                    "params": {"protocolVersion": PROTOCOL, "capabilities": {},
                               "clientInfo": {"name": "influence-dash",
                                              "version": "1"}}})
    _post({"jsonrpc": "2.0", "method": "notifications/initialized"}, sid)
    _, raw = _post({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                    "params": {"name": name, "arguments": args or {}}}, sid)
    m = _parse(raw, 2)
    if "error" in m:
        return {"ok": False, "reason": str(m["error"])[:300]}
    parts = (m.get("result") or {}).get("content", [])
    text = "\n".join(p.get("text", "") for p in parts if p.get("type") == "text")
    try:
        return {"ok": True, "data": json.loads(text) if text else {}}
    except Exception:
        return {"ok": True, "data": {"text": text[:4000]}}


# ---- free reads (no grant needed, $0 + 0 credits) ----

def balance() -> dict:
    r = call_tool("get_credit_balance", {})
    return r


def search_voices(query: str = "", language: str = "", self_only: bool = False,
                  page_size: int = 10) -> dict:
    args: dict = {"page_size": page_size}
    if query:
        args["query"] = query
    if language:
        args["language"] = language
    if self_only:
        args["self"] = True
    return call_tool("search_voices", args)


def estimate_image(workspace_id: str, model_id: str, prompt: str,
                   parameters: dict | None = None, count: int = 1) -> dict:
    return call_tool("estimate_image_generation",
                     {"workspace_id": workspace_id, "model_id": model_id,
                      "prompt": prompt, "parameters": parameters or {},
                      "count": count})


def estimate_video(workspace_id: str, model_id: str, prompt: str,
                  operation: str = "t2v",
                  parameters: dict | None = None) -> dict:
    return call_tool("estimate_video_generation",
                     {"workspace_id": workspace_id, "model_id": model_id,
                      "prompt": prompt, "operation": operation,
                      "parameters": parameters or {}})


def list_media_models(media_type: str = "", capability: str = "") -> dict:
    args: dict = {}
    if media_type:
        args["media_type"] = media_type
    if capability:
        args["capability"] = capability
    return call_tool("list_media_models", args)


def list_workspaces() -> dict:
    return call_tool("list_my_workspaces", {})
