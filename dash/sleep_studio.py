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


# ---- TTS text prep (clean → normalize → chunk → score, pure) ----

def prep_script(raw: str, chunk_limit: int = 1500) -> dict:
    """Snippet-first prep: worthiness before/after, flags, spoken chunks.
    Pure — no network, no spend. Snippet = chunks[0]."""
    sys.path.insert(0, os.path.join(os.path.dirname(SLEEPDRAW), "influence"))
    sys.path.insert(0, os.path.join(os.path.dirname(SLEEPDRAW), "influence",
                                    "pipeline"))
    try:
        import tts_text as _tt
    except ImportError:
        from pipeline import tts_text as _tt
    p = _tt.prep(raw or "", chunk_limit)
    # trim chunk bodies for the UI (full text stays server-side per render)
    p["chunks_preview"] = [c[:120] for c in p["chunks"][:12]]
    return p


# ---- Fish Audio (web-credit voices, grant-gated spend) ----

def _audio_flow():
    sys.path.insert(0, os.path.join(os.path.dirname(SLEEPDRAW), "influence"))
    sys.path.insert(0, os.path.join(os.path.dirname(SLEEPDRAW), "influence",
                                    "pipeline"))
    try:
        import audio_flow as _af
    except ImportError:
        from pipeline import audio_flow as _af
    return _af


def fish_voices(query: str = "", language: str = "en",
                page_size: int = 8) -> dict:
    """Free voice-casting search. Returns voice cards with sample URLs for
    instant in-browser preview (no download needed)."""
    af = _audio_flow()
    r = af.voices(query, language, False, page_size)
    if not r.get("ok"):
        return r
    cards = []
    for v in ((r.get("data") or {}).get("voices") or [])[:page_size]:
        cards.append({"voice_id": v.get("id") or v.get("voice_id"),
                      "name": v.get("title") or v.get("name"),
                      "language": (v.get("languages") or [None])[0],
                      "tags": (v.get("tags") or [])[:6],
                      "sample": v.get("sample_audio"),
                      "task_count": v.get("task_count")})
    return {"ok": True, "cards": cards,
            "page": (r.get("data") or {}).get("page")}


def fish_quote(text: str) -> dict:
    """Pure credit quote for a TTS render. No network, no spend."""
    af = _audio_flow()
    q = af.tts_quote(text or "")
    q["text_chars"] = len(text or "")
    return {"ok": True, "quote": q}


def fish_narrate(text: str, voice_id: str, grant: dict | None = None) -> dict:
    """Fish TTS into the studio voice bank. Dry-run (no grant) returns
    quote + payload_hash for the human to approve. Live (grant) renders,
    downloads the MP3 into VOICE/, and returns the same meta shape as
    narrate() so the existing player just works."""
    af = _audio_flow()
    if not grant:
        return af.speak(text or "", voice_id or "", dry_run=True)
    if not text or len(text) > 15000:
        raise ValueError("text 1..15000 chars (plan per-call budget)")
    r = af.speak(text, voice_id, dry_run=False, ctx={"grant": grant},
                 brand="sleepdraw")
    if not r.get("ok"):
        return r
    url = (((r.get("response") or {}).get("result") or {}).get("data") or {})
    audio_url = url.get("audio_url") or url.get("url") or ""
    if not audio_url and isinstance(url, dict):
        # some responses nest under result.audio
        audio_url = (url.get("result") or {}).get("audio_url", "")
    if not audio_url:
        return {"ok": False, "reason": "tts ok but no audio_url in result"}
    import urllib.request
    SEQ[0] += 1
    name = f"fish-{time.strftime('%H%M%S')}-{SEQ[0]:02d}.mp3"
    out = os.path.join(VOICE, name)
    req = urllib.request.Request(audio_url, headers={"User-Agent": "influence"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        with open(out, "wb") as f:
            f.write(resp.read())
    meta = {"name": name, "voice": f"fish:{voice_id}", "backend": "fish",
            "chars": len(text),
            "credits_quoted": ((r.get("response") or {})
                               .get("credits_quoted")),
            "source_url": audio_url,
            "url": f"/api/studio/file?kind=voice&file={name}"}
    json.dump(meta, open(out + ".json", "w"), indent=1)
    return {"ok": True, **meta}


def list_voice_bank() -> list:
    """Every rendered clip (edge + fish), newest first, player-ready."""
    out = []
    for p in sorted(glob.glob(os.path.join(VOICE, "*.mp3")), reverse=True):
        n = os.path.basename(p)
        m = os.path.join(VOICE, n + ".json")
        meta = json.load(open(m)) if os.path.exists(m) else {}
        meta["name"] = n
        meta.setdefault("url", f"/api/studio/file?kind=voice&file={n}")
        out.append(meta)
    return out


def list_channels() -> list:
    """Channel entities for the dash: every studio/channels/*.json record
    with live status (chairs locked, bank clips, brief present). This is
    the per-channel index — renderers read the record, vaults reference
    it by channel slug."""
    chan_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "studio", "channels")
    chan_dir = os.path.normpath(chan_dir)
    bank = list_voice_bank()
    out = []
    if not os.path.isdir(chan_dir):
        return out
    for fn in sorted(os.listdir(chan_dir)):
        if not fn.endswith(".json") or fn.endswith(".seed.json"):
            continue
        try:
            with open(os.path.join(chan_dir, fn), encoding="utf-8") as f:
                rec = json.load(f)
        except Exception:
            continue
        slug = rec.get("channel", fn[:-5])
        chairs = (rec.get("voice") or {}).get("chairs", {})
        locked = sum(1 for c in chairs.values()
                     if isinstance(c, dict) and c.get("status") == "ear-checked")
        brief = os.path.isfile(os.path.join(chan_dir, slug + "-brief.md"))
        out.append({"slug": slug,
                    "display_name": rec.get("display_name", slug),
                    "status": rec.get("status", "unknown"),
                    "pitch": rec.get("pitch", ""),
                    "engine": (rec.get("engine") or {}).get("primary", ""),
                    "chairs": len(chairs), "chairs_locked": locked,
                    "chair_detail": [
                        {"name": n,
                         "locked": bool(isinstance(c, dict)
                                        and c.get("fish_id")),
                         "label": (c.get("label", "") if isinstance(c, dict)
                                   else ""),
                         "reason": (c.get("lock_reason", "")
                                    if isinstance(c, dict) else "")}
                        for n, c in chairs.items()],
                    "bank_clips": len(bank),
                    "brief": brief,
                    "cadence": rec.get("cadence", "")})
    return out


# ---- Story Studio episodes (native longform via Fish MCP) ----
#
# Snippets → chunk-loop (fish_narrate). EPISODES → Studio projects:
# prep (our QC gate) → import (their LLM structures, free) → generate
# (grant) → export master (grant) → master.mp3 lands in the voice bank.

def studio_import_episode(title: str, raw_script: str,
                          min_score: int = 70) -> dict:
    """Prep-gate then import. Refuses scripts scoring under min_score —
    fix the flags first, don't burn credits on garbage. Free (no audio)."""
    prepped = prep_script(raw_script)
    if prepped["score_after"] < min_score:
        return {"ok": False,
                "reason": f"score {prepped['score_after']} < gate {min_score}",
                "score_before": prepped["score_before"],
                "score_after": prepped["score_after"],
                "flags": prepped["flags_after"][:10],
                "n_chunks": prepped["n_chunks"]}
    af = _audio_flow()
    normed = "\n\n".join(prepped["chunks"])
    r = af.studio_import(normed, name=title)
    if not r.get("ok"):
        return r
    return {"ok": True, "project": (r.get("data") or {}),
            "score": prepped["score_after"],
            "n_chunks": prepped["n_chunks"],
            "credits_total": prepped["credits_total"],
            "next": "poll studio_episode_status, then generate with a grant"}


def studio_episode_status(project_id: str) -> dict:
    """Free poll: chapters, dirty counts, roster, job state."""
    return _audio_flow().studio_status(project_id)


def studio_render_episode(project_id: str, gen_grant: dict) -> dict:
    """Generate (grant) → export QUOTE (free, no grant) → human confirms
    the number → confirmed export goes through audio.studio.export live
    with a second payload-bound grant (dash MCP audio.studio.export)."""
    af = _audio_flow()
    g = af.studio_generate(project_id, dry_run=False,
                           ctx={"grant": gen_grant})
    if not g.get("ok"):
        return {"ok": False, "phase": "generate", **g}
    e = af.studio_export(project_id)
    return {"ok": True, "phase": "generated", "generate": g,
            "export_quote": e,
            "next": "human confirms export credits → audio.studio.export "
                    "live with confirmed_credits + grant → master.mp3"}


def free_narrate(text: str, voice_id: str) -> dict:
    """$0 snippet render (REST s2.1-pro-free) straight into the voice bank.
    No grant, no credits, no dollars — the default ear-check path. Same
    meta shape as narrate()/fish_narrate() so the player just works."""
    af = _audio_flow()
    if not text or not voice_id:
        return {"ok": False, "reason": "text and voice_id required"}
    SEQ[0] += 1
    name = f"free-{time.strftime('%H%M%S')}-{SEQ[0]:02d}.mp3"
    out = os.path.join(VOICE, name)
    r = af.speak_free(text, voice_id, out_path=out)
    if not r.get("ok"):
        return r
    meta = {"name": name, "voice": f"free:{voice_id}", "backend": "free",
            "chars": len(text), "credits_quoted": 0,
            "url": f"/api/studio/file?kind=voice&file={name}"}
    json.dump(meta, open(out + ".json", "w"), indent=1)
    return {"ok": True, **meta}
