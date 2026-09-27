"""Sleep studio backend for the influence dash (Content -> Sleep Studio).

Art (FLUX) -> draw knobs -> render (sleepdraw smooth-stroke) -> voice -> test/.
Powered ONLY by /root/sleepdraw (no powvid imports anywhere).
Secrets stay server-side: CF/R2 creds read from /root/.r2-env in-process.
All state under /root/sleepdraw/runs/studio/{art,renders,voice}.
"""
from __future__ import annotations

import glob
import json
import os
import sys
import threading
import time

SLEEPDRAW = "/root/sleepdraw"
sys.path.insert(0, SLEEPDRAW)
STUDIO = os.path.join(SLEEPDRAW, "runs", "studio")
ART = os.path.join(STUDIO, "art")
REND = os.path.join(STUDIO, "renders")
VOICE = os.path.join(STUDIO, "voice")
os.makedirs(ART, exist_ok=True)
os.makedirs(REND, exist_ok=True)
os.makedirs(VOICE, exist_ok=True)

JOBS: dict = {}
SEQ = [0]

VOICES = {
    # sleep-first shortlist (edge-tts MultilingualNeural, calm + slow by default)
    "aria": "en-US-AriaNeural",       # warm female (SLEEP coin default family)
    "guy": "en-US-GuyNeural",         # calm male narrator
    "ana": "en-US-AnaNeural",         # soft female
    "christopher": "en-US-ChristopherNeural",  # deep male (lore lane)
}


def _creds():
    for line in open(os.environ.get("SLEEPDRAW_ENV_FILE", "/root/.r2-env")):
        line = line.strip()
        if line and "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("'\""))


def _slug(s: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in s.lower())[:40].strip("-")


def lora1() -> dict:
    import yaml
    with open(os.path.join(SLEEPDRAW, "lora1.yaml")) as f:
        return yaml.safe_load(f)


def generate(prompt: str, style: str = "pencil", model: str = "flux") -> dict:
    _creds()
    from sleepdraw.art import STYLES, MODEL_IDS, generate as _gen
    if style not in STYLES:
        raise ValueError(f"style? {sorted(STYLES)}")
    if model not in MODEL_IDS:
        raise ValueError(f"model? {sorted(MODEL_IDS)}")
    img = _gen(prompt, os.environ["CF_API_TOKEN"],
               os.environ["CF_ACCOUNT_ID"], model=model, style=style)
    SEQ[0] += 1
    name = f"{time.strftime('%H%M%S')}-{SEQ[0]:02d}-{_slug(prompt) or 'art'}"
    with open(os.path.join(ART, name + ".jpg"), "wb") as f:
        f.write(img)
    meta = {"name": name, "prompt": prompt, "style": style, "model": model,
            "bytes": len(img)}
    json.dump(meta, open(os.path.join(ART, name + ".json"), "w"), indent=1)
    return meta


def list_art() -> list:
    out = []
    for p in sorted(glob.glob(os.path.join(ART, "*.jpg")), reverse=True):
        n = os.path.basename(p)[:-4]
        m = os.path.join(ART, n + ".json")
        meta = json.load(open(m)) if os.path.exists(m) else {}
        meta["name"] = n
        out.append(meta)
    return out


def _render(name: str, knobs: dict) -> dict:
    from sleepdraw import draw as _draw
    src = os.path.join(ART, name + ".jpg")
    if not os.path.exists(src):
        raise ValueError(f"unknown art '{name}'")
    crop = os.path.join(REND, name + "_16x9.jpg")
    _draw.crop_169(src, crop)
    outdir = os.path.join(REND, f"{name}-{knobs.get('dur', 30000) // 1000}s")
    mp4, frames, log = _draw.render(
        crop, outdir, knobs, duration_ms=knobs.get("dur", 30000),
        no_hand=knobs.get("no_hand", True))
    tag = os.path.basename(outdir)
    return {"mp4": f"/api/studio/file?kind=rend&dir={tag}"
                   f"&file={os.path.basename(mp4)}",
            "mp4path": mp4,
            "frames": [{"t": round(knobs.get("dur", 30000) / 1000 * frac, 1),
                        "url": f"/api/studio/file?kind=rend&dir={tag}"
                               f"&file={os.path.basename(f)}"}
                       for frac, f in zip((0.15, 0.4, 0.65, 0.9), frames)],
            "knobs": knobs, "log": log}


def start_render(name: str, knobs: dict) -> str:
    jid = f"r{int(time.time())}"
    JOBS[jid] = {"status": "running", "name": name, "knobs": knobs}

    def _t():
        try:
            JOBS[jid].update(_render(name, knobs))
            JOBS[jid]["status"] = "done"
        except Exception as e:  # noqa: BLE001
            JOBS[jid] = {"status": "error", "error": str(e)[-1000:]}

    threading.Thread(target=_t, daemon=True).start()
    return jid


def job_status(jid: str) -> dict:
    j = JOBS.get(jid)
    if not j:
        return {"status": "missing"}
    out = dict(j)
    out.pop("mp4path", None)
    return out


def publish(mp4path: str, title: str, recipe: dict) -> dict:
    if not os.path.abspath(mp4path).startswith(REND):
        raise ValueError("mp4 outside studio renders")
    if not os.path.exists(mp4path):
        raise ValueError("mp4 missing")
    from sleepdraw.ship import publish as _pub
    return {"key": _pub(mp4path, title, recipe)}


def narrate(text: str, voice: str = "aria", rate: str = "-5%",
            pitch: str = "-2Hz") -> dict:
    """Voice iteration: edge-tts MP3 into the studio voice bank. No keys needed.
    Rate/pitch follow the SLEEP coin grammar (slow + low)."""
    import asyncio
    import edge_tts
    if voice not in VOICES:
        raise ValueError(f"voice? {sorted(VOICES)}")
    if not text or len(text) > 2000:
        raise ValueError("text 1..2000 chars")
    SEQ[0] += 1
    name = f"narr-{time.strftime('%H%M%S')}-{SEQ[0]:02d}.mp3"
    out = os.path.join(VOICE, name)

    async def _run():
        tts = edge_tts.Communicate(text, VOICES[voice], rate=rate, pitch=pitch)
        await tts.save(out)

    asyncio.run(_run())
    meta = {"name": name, "voice": voice, "rate": rate, "pitch": pitch,
            "chars": len(text),
            "url": f"/api/studio/file?kind=voice&file={name}"}
    json.dump(meta, open(out + ".json", "w"), indent=1)
    return meta
