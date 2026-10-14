"""fal.ai — paid image/video generation. LIVE (key in vault oracle).

Laws: grant-gated (runtime.execute, generate_paid) AND FAL_SPEND_ENABLED=1
(owner kill-switch, default off — same religion as the credit switch).
Default model flux_schnell ($0.01). Router stays cloudflare until a human
picks fal per job. Costs table: pipeline/costs.py fal.*.
"""
from __future__ import annotations

import json
import subprocess
import time
import urllib.request

COST_HINT = "see pipeline/costs.py fal.* (0.01-0.05/image)"

MODELS = {
    "flux_schnell": ("fal-ai/flux/schnell", 0.01),
    "flux_dev": ("fal-ai/flux/dev", 0.025),
    "flux_pro_edit": ("fal-ai/flux-pro/v1/fill", 0.05),
}

QUEUE = "https://queue.fal.run"


def _key() -> str:
    key = __import__("os").environ.get("FAL_KEY", "").strip()
    if key:
        return key
    r = subprocess.run(
        ["agent-vault", "vault", "credential", "get", "FAL_KEY", "--vault",
         "oracle"], capture_output=True, text=True, timeout=15)
    return r.stdout.strip()


def _spend_allowed() -> dict | None:
    import os as _os
    if _os.environ.get("FAL_SPEND_ENABLED", "") != "1":
        return {"ok": False,
                "reason": "FAL SPEND DISABLED (owner policy: $0 until owner "
                          "says otherwise). Cloudflare free path instead."}
    return None


def build_request(prompt: str, model: str = "flux_schnell") -> dict:
    """Pure: describe what WOULD be called. No network, no spend."""
    slug, usd = MODELS.get(model, MODELS["flux_schnell"])
    return {"provider": "fal", "model": model, "endpoint": f"{QUEUE}/{slug}",
            "prompt_chars": len(prompt or ""), "est_usd": usd}


def run(prompt: str, model: str = "flux_schnell",
        ctx: dict | None = None) -> dict:
    """Live text-to-image: queue submit → poll → bytes. Grant + env gate."""
    if not ctx or not ctx.get("grant"):
        return {"ok": False,
                "reason": "no execution context with verified grant: FAIL CLOSED"}
    blocked = _spend_allowed()
    if blocked:
        return blocked
    if not prompt:
        return {"ok": False, "reason": "empty prompt"}
    slug, usd = MODELS.get(model, MODELS["flux_schnell"])
    key = _key()
    if not key:
        return {"ok": False, "reason": "FAL_KEY not in vault oracle"}
    headers = {"Authorization": f"Key {key}",
               "Content-Type": "application/json"}
    body = json.dumps({"prompt": prompt}).encode()
    req = urllib.request.Request(f"{QUEUE}/{slug}", data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            sub = json.load(r)
    except Exception as e:  # noqa: BLE001 — report, never raise spend-side
        return {"ok": False, "reason": f"fal submit: {e}"[:200]}
    rid = sub.get("request_id", "")
    status_url = sub.get("status_url") or f"{QUEUE}/{slug}/requests/{rid}"
    result_url = sub.get("response_url") or status_url
    for _ in range(20):
        time.sleep(6)
        try:
            with urllib.request.urlopen(
                    urllib.request.Request(
                        status_url,
                        headers={"Authorization": f"Key {key}"}),
                    timeout=30) as r:
                st = json.load(r)
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "reason": f"fal poll: {e}"[:200]}
        if str(st.get("status", "")).upper() in ("COMPLETED", "DONE"):
            result_url = st.get("response_url", result_url)
            break
        if str(st.get("status", "")).upper() in ("FAILED", "ERROR"):
            return {"ok": False,
                    "reason": f"fal job failed: {st}"[:200]}
    try:
        with urllib.request.urlopen(
                urllib.request.Request(result_url, headers={
                    "Authorization": f"Key {key}"}), timeout=60) as r:
            res = json.load(r)
        img = (res.get("images") or [{}])[0].get("url", "")
        with urllib.request.urlopen(img, timeout=120) as r:
            data = r.read()
        return {"ok": True, "image_bytes": data, "model": model,
                "cost_usd": usd}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "reason": f"fal fetch: {e}"[:200]}
