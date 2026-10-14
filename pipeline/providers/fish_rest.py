"""Fish REST provider — the $0 pro-quality path (s2.1-pro-free).

Different wallet from the MCP: this bills NOTHING (free tier, fair use),
not package credits, not API dollars. Use for tests, casting ear-checks,
snippets, and bulk narration where Drama direction isn't needed.

Key: characters/audition/.env ONLY (600, gitignored). Never in repo.
No grant needed ($0 = no consequence) but every call is logged by the
caller for the receipts trail.
"""
from __future__ import annotations

import json
import os
import urllib.request

API_BASE = "https://api.fish.audio"
MODEL_FREE = "s2.1-pro-free"   # $0, pro quality, unlimited fair-use
MODEL_PRO = "s2.1-pro"         # $15/M bytes — ASK FIRST, never default
PER_CALL_BYTES = 15000

_KEY_PATHS = [
    "/root/characters/audition/.env",
    os.path.join(os.path.expanduser("~"), ".fish-env"),
]


def api_key() -> str:
    env = os.environ.get("FISH_API_KEY", "").strip()
    if env:
        return env
    for p in _KEY_PATHS:
        try:
            with open(p, encoding="utf-8") as f:
                for line in f:
                    if line.startswith("FISH_API_KEY="):
                        return line.strip().split("=", 1)[1]
        except OSError:
            continue
    raise SystemExit("fish_rest: no FISH_API_KEY (audition/.env or ~/.fish-env)")


def tts(text: str, voice_id: str, model: str = MODEL_FREE,
        out_path: str = "") -> dict:
    """Render MP3 bytes. Defaults to the FREE model; anything else raises
    unless explicitly passed (callers gate paid models behind grants)."""
    if model != MODEL_FREE:
        raise PermissionError(f"fish_rest: model {model} is billed — use the "
                              "grant-gated MCP path instead")
    n = len((text or "").encode("utf-8"))
    if n == 0:
        return {"ok": False, "reason": "empty text"}
    if n > PER_CALL_BYTES:
        return {"ok": False,
                "reason": f"{n} bytes over per-call budget — split first"}
    req = urllib.request.Request(
        f"{API_BASE}/v1/tts",
        data=json.dumps({"text": text, "reference_id": voice_id,
                         "format": "mp3", "normalize": True}).encode(),
        headers={"Authorization": f"Bearer {api_key()}",
                 "Content-Type": "application/json", "model": model})
    with urllib.request.urlopen(req, timeout=120) as r:
        audio = r.read()
    if out_path:
        with open(out_path, "wb") as f:
            f.write(audio)
    return {"ok": True, "model": model, "bytes": len(audio),
            "usd": 0.0, "credits": 0, "path": out_path or ""}


def voice_design(instruction: str, n: int = 2, language: str = "en",
                 reference_text: str = "", speed: float = 1.0,
                 approved: bool = False) -> dict:
    """Generate original voices from a text prompt ($0.01/request, API
    dollars — NOT free tier, NOT package credits). REQUIRES approved=True
    with explicit owner yes. Returns candidates with base64 preview audio.
    P0 engine for prompting the perfect narrator voice per channel."""
    if not approved:
        raise PermissionError("voice_design bills $0.01/request: pass "
                              "approved=True with explicit owner yes")
    if not instruction or len(instruction) > 2000:
        return {"ok": False, "reason": "instruction 1..2000 chars"}
    body: dict = {"instruction": instruction, "language": language,
                  "n": max(1, min(4, n)), "speed": speed}
    if reference_text:
        body["reference_text"] = reference_text[:150]
    req = urllib.request.Request(
        f"{API_BASE}/v1/voice-design", data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {api_key()}",
                 "Content-Type": "application/json",
                 "model": "voice-design-1"})
    with urllib.request.urlopen(req, timeout=180) as r:
        data = json.load(r)
    cands = []
    for c in data.get("candidates", []):
        cands.append({"voice_id": c.get("id") or c.get("voice_id") or "",
                      "title": c.get("title") or "",
                      "audio_b64": (c.get("audio") or "")[:50] + "..."
                      if c.get("audio") else "",
                      "_audio_b64_full": c.get("audio") or ""})
    return {"ok": True, "model": "voice-design-1", "usd": 0.01,
            "instruction": instruction, "candidates": cands}
