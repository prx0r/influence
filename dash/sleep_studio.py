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
import re
import sys
import threading
import time

SLEEPDRAW = os.environ.get("SLEEPDRAW_DIR", "/root/sleepdraw")
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
    _repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for _p in (_repo, os.path.join(_repo, "pipeline")):
        if _p not in sys.path:
            sys.path.append(_p)  # this checkout, after the /root tree
    try:
        import tts_text as _tt
    except ImportError:
        from pipeline import tts_text as _tt
    p = _tt.prep(raw or "", chunk_limit)
    # trim chunk bodies for the UI (full text stays server-side per render)
    p["chunks_preview"] = [c[:120] for c in p["chunks"][:12]]
    return p


# ---- pilot → collection map (which book each script came from) ----
# Keys: pilot filename stems. Value: (collection dir, season).
# tale: groups cuts of the SAME story (doorway excerpt + full + verbatim
# are one tale, three cuts — not three videos). Fallback for unmapped:
# house as collection, filename as tale.

_PILOT_COLLECTIONS = {
    "01-yuki-doorway": ("kwaidan-part-1", "S2-folklore", "yuki-onna", "excerpt"),
    "01-yuki-onna-full-tale": ("kwaidan-part-1", "S2-folklore", "yuki-onna", "full"),
    "01-yuki-onna-verbatim": ("kwaidan-part-1", "S2-folklore", "yuki-onna", "verbatim"),
    "02-little-mermaid": ("andersen-part-1", "S1-fairy", "little-mermaid", "full"),
    "03-baba-yaga": ("russian-fairy-tales-part-1", "S2-folklore", "baba-yaga", "full"),
    "04-punchkin": ("russian-fairy-tales-part-1", "S2-folklore", "punchkin", "full"),
    "05-deccan-sun-moon-wind": ("russian-fairy-tales-part-3", "S2-folklore", "deccan-sun-moon-wind", "full"),
    "06-aesop-fables": ("aesop-front-to-back", "S1-fairy", "aesop-fables", "full"),
}


def _pilot_collection(path: str, house: str) -> dict:
    """Collection + tale + cut for a pilot file. Numbering assigned later,
    per collection group (kwaidan 01-03, andersen 01)."""
    stem = os.path.basename(path).split(".")[0]
    if stem in _PILOT_COLLECTIONS:
        coll, season, tale, cut = _PILOT_COLLECTIONS[stem]
    else:
        tale = re.sub(r"^\d+[\-_ ]+", "", stem).replace("-", " ")
        coll, season, cut = house, "S?-unknown", "full"
    short = re.sub(r"^\d+[\-_ ]+", "", stem).replace("-", " ")
    prefix = "FF" if house == "folk-and-fable" else "".join(
        w[0] for w in house.split("-") if w).upper()[:4]
    return {"collection": coll, "season": season, "tale": tale, "cut": cut,
            "video_id": f"{prefix}-{season}-{coll}-00",
            "title": short.title()}


# ---- damn pilots: drama.txt → per-speaker $0 renders → master ----
#
# damn owns scripts + routines (readout/gate/poison over there); WE own
# execution. Pilot files declare chairs + voice IDs in // headers; locked
# channel chairs override stand-ins. Each speaker segment renders on its
# own chair voice (free tier), concatenated to one master in the bank.
# Their gate.py + tts-poison.py run as extra validators (imported, not
# copied). No duplication: scripts live in damn, audio lands here.

DAMN = os.environ.get("DAMN_DIR", "/root/damn")


def _damn_gate():
    import importlib.util as _ilu
    mod = _ilu.spec_from_file_location(
        "damn_gate", os.path.join(DAMN, "fish", "gate.py"))
    g = _ilu.module_from_spec(mod)
    mod.loader.exec_module(g)
    return g


def _damn_poison():
    import importlib.util as _ilu
    mod = _ilu.spec_from_file_location(
        "damn_tts_poison", os.path.join(DAMN, "fish", "tts-poison.py"))
    g = _ilu.module_from_spec(mod)
    mod.loader.exec_module(g)
    return g


def list_pilots() -> list:
    """Every pilots/*.drama.txt + videos/*.drama.txt with readiness
    (our prep score + their gate + poison). Pure reads until render."""
    import glob as _glob
    sys.path.insert(0, os.path.join(os.path.dirname(SLEEPDRAW), "influence"))
    sys.path.insert(0, os.path.join(os.path.dirname(SLEEPDRAW), "influence",
                                    "pipeline"))
    _repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for _p in (_repo, os.path.join(_repo, "pipeline")):
        if _p not in sys.path:
            sys.path.append(_p)  # this checkout, after the /root tree
    try:
        import tts_text as _tt
    except ImportError:
        from pipeline import tts_text as _tt
    out = []
    for path in sorted(_glob.glob(os.path.join(
            DAMN, "projects", "*", "pilots", "*.drama.txt"))) + sorted(
            _glob.glob(os.path.join(DAMN, "projects", "*", "videos",
                                    "*.drama.txt"))) + sorted(
            _glob.glob(os.path.join(DAMN, "projects", "*", "readout",
                                    "*.read.txt"))):
        try:
            raw = open(path, encoding="utf-8", errors="replace").read()
            body = "\n".join(l for l in raw.splitlines()
                             if not l.startswith("//")).strip()
            p = _tt.prep(body)
            gate, poison = {"pass": None}, {"pass": None}
            try:
                gate = _damn_gate().gate(body)
            except Exception:
                pass
            try:
                poison = _damn_poison().poison(body)
            except Exception:
                pass
            house = path.split(os.sep)[-3]
            kind = ("pilot" if "/pilots/" in path else
                    "readout" if "/readout/" in path else "video")
            out.append({"path": path, "house": house, "kind": kind,
                        "file": os.path.basename(path),
                        **_pilot_collection(path, house),
                        "score": p["score_after"],
                        "chunks": p["n_chunks"],
                        "credits_or_free": p["credits_total"],
                        "gate": bool(gate.get("pass")),
                        "poison": bool(poison.get("pass")),
                        "ready": p["score_after"] >= 70 and gate.get("pass")
                        and poison.get("pass")})
        except Exception as e:  # noqa: BLE001 — one bad file can't kill list
            out.append({"path": path, "house": "?", "kind": "?",
                        "file": os.path.basename(path),
                        "ready": False, "reason": str(e)[:120]})
    # number video IDs within each collection (kwaidan 01-03, andersen 01)
    counters: dict = {}
    for o in out:
        key = (o.get("house"), o.get("collection"))
        counters[key] = counters.get(key, 0) + 1
        if o.get("video_id"):
            o["video_id"] = re.sub(r"-\d+$", f"-{counters[key]:02d}",
                                   o["video_id"])
    return out


def parse_drama(path: str) -> dict:
    """drama.txt (or readout .read.txt) → header chairs + speaker segments.
    Path-guarded to damn. Readout files have no speaker tags: single
    speaker 0 (narrator resolves from channel lock or override)."""
    full = os.path.realpath(path)
    if not full.startswith(os.path.realpath(DAMN) + os.sep):
        raise ValueError("pilot outside damn/")
    if ((not full.endswith(".drama.txt") and not full.endswith(".read.txt"))
            or not os.path.isfile(full)):
        raise ValueError("not a damn pilot/readout file")
    raw = open(full, encoding="utf-8", errors="replace").read()
    chairs: dict = {}
    for ln in raw.splitlines():
        if not ln.startswith("//"):
            continue
        m = re.match(r"//\s*(\w+)\s+<\|speaker:(\d+)\|>\s*(\S+)?\s*([0-9a-f]{32})?",
                     ln)
        if m:
            chairs[m.group(1)] = {"speaker": int(m.group(2)),
                                  "label": m.group(3) or "",
                                  "voice_id": m.group(4) or ""}
    body = "\n".join(l for l in raw.splitlines()
                     if not l.startswith("//")).strip()
    # split body on speaker tags, keeping text per speaker
    import re as _re2
    parts = _re2.split(r"(<\|speaker:\d+\|>)", body)
    segs, cur_spk, buf = [], 0, []
    for part in parts:
        mm = _re2.fullmatch(r"<\|speaker:(\d+)\|>", part.strip())
        if mm:
            if buf:
                segs.append({"speaker": cur_spk,
                             "text": "\n".join(buf).strip()})
                buf = []
            cur_spk = int(mm.group(1))
        elif part.strip():
            buf.append(part.strip())
    if buf:
        segs.append({"speaker": cur_spk, "text": "\n".join(buf).strip()})
    segs = [s for s in segs if s["text"]]
    return {"path": full, "house": full.split(os.sep)[-3],
            "chairs": chairs, "segments": segs,
            "n_segments": len(segs)}


def render_pilot(path: str, channel_slug: str = "",
                 voice_overrides: dict | None = None,
                 min_score: int = 70,
                 speaker_voices: dict | None = None,
                 speed: float | None = None,
                 temperature: float | None = None,
                 volume_db: float = 0.0,
                 max_segments: int = 0,
                 tag_prefix: str = "pilot",
                 extra_meta: dict | None = None) -> dict:
    """Batch a damn pilot to a master MP3 — $0, no grants, no credits.
    Prep-gate + damn gate + poison per segment, per-speaker free renders
    (locked channel chairs override header stand-ins), ffmpeg concat.
    speaker_voices maps raw speaker numbers when the file declares no
    header chairs: {0: vid, 1: vid}."""
    import subprocess as _sp
    import time as _time
    sys.path.insert(0, os.path.join(os.path.dirname(SLEEPDRAW), "influence"))
    sys.path.insert(0, os.path.join(os.path.dirname(SLEEPDRAW), "influence",
                                    "pipeline"))
    _repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for _p in (_repo, os.path.join(_repo, "pipeline")):
        if _p not in sys.path:
            sys.path.append(_p)  # this checkout, after the /root tree
    try:
        import tts_text as _tt
    except ImportError:
        from pipeline import tts_text as _tt
    parsed = parse_drama(path)
    # locked chairs override stand-in IDs from the header
    locked: dict = {}
    if channel_slug:
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from channel_character import load_channel
            ch = load_channel(channel_slug)
            for nm, c in (((ch.get("voice") or {}).get("chairs")) or {}).items():
                if isinstance(c, dict) and c.get("fish_id"):
                    locked[nm] = c["fish_id"]
        except Exception:
            pass
    spk_voice: dict = {}
    for cname, c in parsed["chairs"].items():
        if cname in (voice_overrides or {}):
            spk_voice[c["speaker"]] = (voice_overrides or {})[cname]
        elif cname in locked:
            spk_voice[c["speaker"]] = locked[cname]
        elif c.get("voice_id"):
            spk_voice[c["speaker"]] = c["voice_id"]
    # explicit speaker map wins over everything (auditioning new voices)
    for spk, vid in (speaker_voices or {}).items():
        try:
            spk_voice[int(spk)] = vid
        except (TypeError, ValueError):
            continue
    # readout files: no chairs at all → channel narrator lock carries it
    if not spk_voice and 0 not in spk_voice:
        narr = next((v for k, v in locked.items()
                     if "narr" in k.lower()), None) or next(iter(locked.values()), None)
        if narr:
            spk_voice[0] = narr
    if not spk_voice:
        return {"ok": False, "reason": "no voices: header has no IDs and "
                "no locked chairs (pass voice_overrides)"}
    gate = _damn_gate()
    try:
        poison = _damn_poison()
    except Exception:
        poison = None
    SEQ[0] += 1
    tag = f"{tag_prefix}-{_time.strftime('%H%M%S')}-{SEQ[0]:02d}"
    if max_segments and max_segments > 0:
        # preview: first N segments only (the vibe check, not the episode)
        parsed = dict(parsed, segments=parsed["segments"][:max_segments])
    seg_paths = []
    receipt = {"pilot": parsed["path"], "house": parsed["house"],
               "channel": channel_slug, "segments": []}
    for i, s in enumerate(parsed["segments"]):
        vid = spk_voice.get(s["speaker"])
        if not vid:
            return {"ok": False,
                    "reason": f"speaker {s['speaker']} has no voice"}
        prepped = _tt.prep(s["text"])
        if prepped["score_after"] < min_score:
            return {"ok": False,
                    "reason": f"segment {i} score {prepped['score_after']} "
                              f"< gate {min_score}",
                    "flags": prepped["flags_after"][:6]}
        try:
            if not gate.gate(s["text"])["pass"]:
                return {"ok": False,
                        "reason": f"segment {i} blocked by damn gate"}
        except Exception as e:  # noqa: BLE001 — gate infra hiccup, report
            return {"ok": False, "reason": f"gate error seg {i}: {e}"[:120]}
        if poison is not None:
            try:
                if not poison.poison(s["text"])["pass"]:
                    return {"ok": False,
                            "reason": f"segment {i} blocked by tts-poison"}
            except Exception as e:  # noqa: BLE001
                return {"ok": False, "reason": f"poison error seg {i}: {e}"[:120]}
        # render each prep chunk to bank parts (free tier, saved files).
        # Channel pace → prosody speed (sleep recipe; neutral 1.0 default).
        af = _audio_flow()
        part_paths = []
        seg_speed = 1.0
        if channel_slug:
            try:
                from channel_character import load_channel as _lc
                seg_speed = float(
                    ((_lc(channel_slug).get("voice") or {}).get("pace")) or 1.0)
            except Exception:
                seg_speed = 1.0
        if speed is not None:
            seg_speed = max(0.5, min(2.0, float(speed)))
        for j, ch_text in enumerate(prepped["chunks"]):
            pp = os.path.join(VOICE, f"{tag}-s{i:02d}p{j}.mp3")
            r = af.speak_free(ch_text, vid, out_path=pp, speed=seg_speed,
                              volume_db=volume_db, temperature=temperature)
            if not r.get("ok") or not os.path.exists(pp):
                return {"ok": False,
                        "reason": f"segment {i} render failed: "
                                  f"{r.get('reason', 'no file')}"}
            part_paths.append(pp)
        seg_paths.extend(part_paths)
        receipt["segments"].append({
            "i": i, "speaker": s["speaker"], "voice_id": vid,
            "score": prepped["score_after"],
            "chars": sum(len(c.encode()) for c in prepped["chunks"]),
            "parts": [os.path.basename(p) for p in part_paths]})
        _time.sleep(0.3)  # fair-use pacing between free calls
    # concat to master
    lst = os.path.join(VOICE, tag + ".lst")
    with open(lst, "w") as f:
        for p in seg_paths:
            f.write(f"file '{p}'\n")
    master = os.path.join(VOICE, tag + "-master.mp3")
    r = _sp.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst,
                 "-c", "copy", master],
                capture_output=True, text=True)
    for p in seg_paths + [lst]:
        try:
            os.remove(p)
        except OSError:
            pass
    if r.returncode != 0 or not os.path.exists(master):
        return {"ok": False, "reason": "ffmpeg concat failed: "
                + (r.stderr or "")[-200:]}
    meta = {"name": os.path.basename(master),
            "voice": f"pilot:{parsed['house']}",
            "backend": "free-batch", "chars": sum(
                s["chars"] for s in receipt["segments"]),
            "credits_quoted": 0, "pilot": receipt,
            "url": f"/api/studio/file?kind=voice&file={os.path.basename(master)}"}
    if extra_meta:
        meta.update({k: v for k, v in extra_meta.items()
                     if k not in ("name", "url")})
    json.dump(meta, open(master + ".json", "w"), indent=1)
    return {"ok": True, **meta}


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
    """Every rendered clip (edge + fish), newest first, player-ready.
    Includes R2-archived clips (mp3 pruned, meta + r2_key kept) — the
    file route 302s those to presigned URLs."""
    out, seen = [], set()
    for p in sorted(glob.glob(os.path.join(VOICE, "*.mp3")), reverse=True):
        n = os.path.basename(p)
        m = os.path.join(VOICE, n + ".json")
        meta = json.load(open(m)) if os.path.exists(m) else {}
        meta["name"] = n
        meta.setdefault("url", f"/api/studio/file?kind=voice&file={n}")
        out.append(meta)
        seen.add(n)
    for m in sorted(glob.glob(os.path.join(VOICE, "*.json")), reverse=True):
        try:
            meta = json.load(open(m))
        except Exception:
            continue
        nm = meta.get("name", os.path.basename(m)[:-5])
        if nm in seen or not meta.get("r2_key"):
            continue
        meta["name"] = nm
        meta.setdefault("url", f"/api/studio/file?kind=voice&file={nm}")
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
        if (not fn.endswith(".json") or fn.endswith(".seed.json")
                or fn.endswith("-taste.json")):
            continue
        try:
            with open(os.path.join(chan_dir, fn), encoding="utf-8") as f:
                rec = json.load(f)
        except Exception:
            continue
        if not isinstance(rec, dict) or not rec.get("channel"):
            continue  # taste files, seeds, fragments are not channels
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


def free_narrate(text: str, voice_id: str, speed: float = 1.0) -> dict:
    """$0 snippet render (REST s2.1-pro-free) straight into the voice bank.
    No grant, no credits, no dollars — the default ear-check path. Same
    meta shape as narrate()/fish_narrate() so the player just works.
    speed: channel pace (sleep houses ~0.85, recipe 0.72)."""
    af = _audio_flow()
    if not text or not voice_id:
        return {"ok": False, "reason": "text and voice_id required"}
    SEQ[0] += 1
    name = f"free-{time.strftime('%H%M%S')}-{SEQ[0]:02d}.mp3"
    out = os.path.join(VOICE, name)
    r = af.speak_free(text, voice_id, out_path=out, speed=speed)
    if not r.get("ok"):
        return r
    meta = {"name": name, "voice": f"free:{voice_id}", "backend": "free",
            "chars": len(text), "credits_quoted": 0,
            "url": f"/api/studio/file?kind=voice&file={name}"}
    json.dump(meta, open(out + ".json", "w"), indent=1)
    return {"ok": True, **meta}


# ---- voice-design casting engine (P0: prompt the perfect narrator) ----
#
# Channel record → instruction prompt → Fish voice-design ($0.01/req,
# approved-only) → preview MP3s in the bank → human locks. The instruction
# builder IS the engine: chair direction + nevers + pace + shelf + pitch.

def design_instruction(channel_slug: str, chair: str = "narrator") -> dict:
    """Build the voice-design prompt for a chair. Pure, $0, no approval."""
    sys.path.insert(0, os.path.join(os.path.dirname(SLEEPDRAW), "influence"))
    sys.path.insert(0, os.path.join(os.path.dirname(SLEEPDRAW), "influence",
                                    "pipeline"))
    try:
        import channel_character
    except ImportError:
        from pipeline import channel_character
    try:
        ch = channel_character.load_channel(channel_slug)
    except OSError:
        return {"ok": False, "reason": f"unknown channel {channel_slug}"}
    chairs = (ch.get("voice") or {}).get("chairs", {})
    c = chairs.get(chair)
    if not c:
        return {"ok": False,
                "reason": f"no chair '{chair}' (have: {sorted(chairs)})"}
    pace = ((ch.get("voice") or {}).get("pace") or 1.0)
    parts = [f"{c.get('label', chair)}.",
             f"{c.get('direction', '')}."]
    if c.get("never"):
        parts.append(f"Never {', '.join(c['never'][:4])}.")
    if pace != 1.0:
        parts.append("Slower than normal speech." if pace < 1.0
                     else "Brisker than normal speech.")
    parts.append(f"For {ch.get('display_name', channel_slug)} sleep content: "
                 f"{ch.get('pitch', '')}")
    instruction = " ".join(p for p in parts if p)[:1800]
    return {"ok": True, "channel": channel_slug, "chair": chair,
            "instruction": instruction}


def design_voice(channel_slug: str, chair: str = "narrator", n: int = 2,
                 approved: bool = False) -> dict:
    """Generate + bank original voice candidates. $0.01/req — approved only."""
    import base64 as _b64
    ins = design_instruction(channel_slug, chair)
    if not ins.get("ok"):
        return ins
    sys.path.insert(0, os.path.join(os.path.dirname(SLEEPDRAW), "influence"))
    sys.path.insert(0, os.path.join(os.path.dirname(SLEEPDRAW), "influence",
                                    "pipeline"))
    try:
        from providers import fish_rest
    except ImportError:
        from pipeline.providers import fish_rest
    r = fish_rest.voice_design(ins["instruction"], n=n, approved=approved)
    if not r.get("ok"):
        return r
    SEQ[0] += 1
    previews = []
    for i, c in enumerate(r.get("candidates", [])):
        raw = c.get("_audio_b64_full", "")
        if not raw:
            continue
        nm = (f"designed-{time.strftime('%H%M%S')}-{SEQ[0]:02d}-{i}.mp3")
        out = os.path.join(VOICE, nm)
        with open(out, "wb") as f:
            f.write(_b64.b64decode(raw))
        meta = {"name": nm, "voice": f"designed:{c.get('voice_id', '')[:8]}",
                "backend": "voice-design", "instruction": ins["instruction"],
                "usd": 0.01,
                "url": f"/api/studio/file?kind=voice&file={nm}"}
        json.dump(meta, open(out + ".json", "w"), indent=1)
        previews.append({"name": nm, "voice_id": c.get("voice_id", ""),
                         "title": c.get("title", ""), "url": meta["url"]})
    return {"ok": True, "channel": channel_slug, "chair": chair,
            "instruction": ins["instruction"], "usd": 0.01,
            "previews": previews,
            "next": "listen → lock the winner via casting UI with a reason"}


# ---- go button: collection → cast sheet + sample per speaker ($0) ----
#
# Press go on a collection: dramatis exists → ensemble briefs → top
# speakers searched (free) → one sample line each rendered free → bank.
# Human + pi review the sheet, lock voices, then batch renders.

def prepare_cast(collection: str, channel_slug: str = "",
                 max_cast: int = 6) -> dict:
    """Full cast prep for one collection. Free reads + $0 renders only."""
    import json as _json
    sys.path.insert(0, os.path.join(os.path.dirname(SLEEPDRAW), "influence"))
    sys.path.insert(0, os.path.join(os.path.dirname(SLEEPDRAW), "influence",
                                    "pipeline"))
    try:
        from ensemble_cast import compose_cast, contrast_notes
    except ImportError:
        from pipeline.ensemble_cast import compose_cast, contrast_notes
    af = _audio_flow()
    dpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                         "studio", "channels",
                         (channel_slug or "folk-and-fable"),
                         "dramatis", collection + ".json")
    dpath = os.path.normpath(dpath)
    if ".." in os.path.relpath(dpath, os.path.normpath(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                         "studio", "channels"))):
        return {"ok": False, "reason": "bad collection"}
    try:
        with open(dpath, encoding="utf-8") as f:
            dram = _json.load(f)
    except OSError:
        return {"ok": False, "reason": f"no dramatis for {collection}"}
    cast = compose_cast(dram.get("characters", []),
                        context=f"{channel_slug} sleep storytelling",
                        max_cast=max_cast)
    for c in cast:
        v = af.voices(c["voice_query"], "en", False, 3)
        cands = []
        for vrow in ((v.get("data") or {}).get("voices") or [])[:3]:
            cands.append({"voice_id": vrow.get("id"),
                          "name": vrow.get("title"),
                          "sample": vrow.get("sample_audio"),
                          "uses": vrow.get("task_count")})
        c["candidates"] = cands
        line = (c.get("sample_line") or
                f"I am {c['name']}. Listen well, for this tale is old.")[:220]
        if cands:
            m = free_narrate(line, cands[0]["voice_id"])
            c["audition"] = {"clip": m.get("name"), "url": m.get("url"),
                             "voice_id": cands[0]["voice_id"],
                             "ok": m.get("ok")}
        import time as _t
        _t.sleep(0.3)
    sheet = {"ok": True, "collection": collection, "channel": channel_slug,
             "cast": cast, "contrast_notes": contrast_notes(cast),
             "next": "human + pi review sheet → lock voices → batch render"}
    cdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                        "studio", "channels", channel_slug or "folk-and-fable",
                        "casts")
    cdir = os.path.normpath(cdir)
    if cdir.startswith(os.path.normpath(os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "studio",
            "channels")) + os.sep):
        os.makedirs(cdir, exist_ok=True)
        with open(os.path.join(cdir, collection + ".cast.json"), "w",
                  encoding="utf-8") as f:
            json.dump(sheet, f, indent=1, ensure_ascii=False)
        sheet["saved"] = f"studio/channels/{channel_slug}/casts/{collection}.cast.json"
    return sheet


# ---- character context: who is this, in the books' own words ----

def character_context(channel_slug: str, chair: str) -> dict:
    """Who is this character? Aggregated from the channel's dramatis files:
    books they appear in, profile, and actual sample lines from the books.
    Powers human casting tasks ('confirm the voice for X')."""
    import glob as _glob
    ddir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                        "studio", "channels", channel_slug, "dramatis")
    ddir = os.path.normpath(ddir)
    if (".." in os.path.relpath(ddir, os.path.normpath(os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "studio",
            "channels")))):
        return {"ok": False, "reason": "bad channel"}
    books, profiles = [], {}
    sensible = chair.strip().lower()
    for fp in sorted(_glob.glob(os.path.join(ddir, "*.json"))):
        try:
            d = json.load(open(fp, encoding="utf-8"))
        except Exception:
            continue
        for c in d.get("characters", []):
            nm = str(c.get("name", ""))
            if nm.lower() == sensible or sensible in nm.lower():
                books.append(os.path.basename(fp)[:-5])
                profiles[nm] = {
                    "mentions": c.get("mentions", 0),
                    "dialogue_lines": c.get("dialogue_lines", 0),
                    "gender": c.get("gender"), "age": c.get("age"),
                    "role": c.get("role"),
                    "voice_query": c.get("voice_query", ""),
                    "sample_line": (c.get("sample_line", "") or "").strip(
                        "“”\"' \n")[:220],
                    "dialogue_how": c.get("dialogue_how", "")}
    if not profiles:
        return {"ok": False,
                "reason": f"no book character matches '{chair}'"}
    return {"ok": True, "chair": chair, "books": sorted(set(books)),
            "characters": profiles}


# ---- per-video workspace: script + voices + titles + thumb in one view ----

_TRADITIONS = {"yuki": "Japanese Folklore", "kwaidan": "Japanese Folklore",
               "mermaid": "Danish Fairytale", "andersen": "Danish Fairytale",
               "baba": "Russian Folklore", "grimm": "German Fairytale",
               "anansi": "West African Folklore", "cyclops": "Greek Myth",
               "orpheus": "Greek Myth", "rapunzel": "German Fairytale",
               "snow-queen": "Danish Fairytale", "puss": "French Fairytale"}


def _tradition(slug: str) -> str:
    low = slug.lower()
    for k, v in _TRADITIONS.items():
        if k in low:
            return v
    return ""


def video_detail(path: str, channel_slug: str = "") -> dict:
    """One video workspace: script meta, voice map, title drafts, thumb
    draft. All free reads + $0 local compose. Picks save to bgraph item."""
    import sys as _s
    _s.path.insert(0, os.path.join(os.path.dirname(SLEEPDRAW), "influence"))
    _s.path.insert(0, os.path.join(os.path.dirname(SLEEPDRAW), "influence",
                                   "pipeline"))
    from pipeline.titles import draft as _titles
    try:
        import tts_text as _tt
    except ImportError:
        from pipeline import tts_text as _tt
    parsed = parse_drama(path)
    body = "\n".join(s["text"] for s in parsed["segments"])
    prep = _tt.prep(body[:6000])
    words = len(body.split())
    slug = os.path.basename(path).split(".")[0]
    dur = f"{round(words / 105)} min" if words else ""
    tale = re.sub(r"^\d+[\-_ ]+", "", slug).replace("-", " ").strip()
    vid = re.sub(r"[^A-Za-z0-9]+", "-", slug).strip("-")[:60]
    pref = []
    try:
        _vp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                           "studio", "video-picks.json")
        _allp = json.load(open(os.path.normpath(_vp), encoding="utf-8"))
        for _pid, _pk in _allp.items():
            if isinstance(_pk, dict) and _pk.get("title"):
                pref.append(_pk.get("formula") or "")
    except Exception:
        pass
    titles = _titles(tale, _tradition(slug), dur,
                     [p for p in pref if p] or None)
    # voice map: locked channel chairs override header stand-ins.
    # Header maps chair name -> speaker number, so each spk entry shows
    # the LOCKED voice wherever known (no duplicate stand-in rows).
    vmap: dict = {}
    locked_by_chair: dict = {}
    if channel_slug:
        try:
            from channel_character import load_channel
            ch = load_channel(channel_slug)
            for nm, c in (((ch.get("voice") or {}).get("chairs")) or {}).items():
                if isinstance(c, dict) and c.get("fish_id"):
                    vmap[nm] = {"voice_id": c["fish_id"],
                                "label": (c.get("label", "") or "") + " (locked)"}
                    locked_by_chair[nm] = c["fish_id"]
        except Exception:
            pass
    for cname, c in parsed["chairs"].items():
        if cname in locked_by_chair:
            continue  # already shown as the locked chair above
        vmap.setdefault("spk" + str(c["speaker"]),
                        {"voice_id": c.get("voice_id", ""),
                         "label": cname + " (script stand-in)"})
    # thumb draft: channel art + short title, local compose ($0)
    thumb = None
    try:
        from pipeline.thumb import compose as _compose
        art = "/root/sleepdraw/assets/moon-lora1-flux-pencil.jpg"
        short = " ".join(tale.split()[:3]).title()
        tdir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "pipeline", "runs", channel_slug or "studio",
                            "thumbs")
        os.makedirs(tdir, exist_ok=True)
        tp = os.path.join(tdir, slug + "-draft.jpg")
        r = _compose(art, short, tp)
        if r.get("ok"):
            thumb = {"path": tp, "bytes": r["bytes"], "title": short}
    except Exception as e:  # noqa: BLE001 — thumb draft is best-effort
        thumb = {"error": str(e)[:120]}
    return {"ok": True, "slug": slug, "house": parsed["house"],
            "words": words, "minutes": round(words / 105, 1),
            "segments": parsed["n_segments"],
            "score": prep["score_after"],
            "titles": titles, "voice_map": vmap, "thumb_draft": thumb,
            "chairs": parsed["chairs"]}


def save_video_picks(video_id: str, title: str = "", thumb_path: str = "",
                     voice_map: dict | None = None,
                     formula: str = "") -> dict:
    """Save human picks onto the bgraph video item. Picks train future
    drafts (preferred title formulas rank first). Path-guarded IDs."""
    import re as _re2
    if not _re2.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{1,80}", video_id or ""):
        return {"ok": False, "reason": "bad video id"}
    p = os.path.join("/root/bgraph/registry/content/items", video_id + ".json")
    if not os.path.isfile(p):
        # pilots not yet registered get a lightweight local record
        p = None
        reg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                           "studio", "video-picks.json")
        reg = os.path.normpath(reg)
        try:
            allp = json.load(open(reg, encoding="utf-8"))
        except Exception:
            allp = {}
        allp[video_id] = {"title": title[:120], "thumb": thumb_path[:200],
                          "voices": voice_map or {},
                          "formula": formula[:60],
                          "at": int(time.time())}
        with open(reg, "w", encoding="utf-8") as f:
            json.dump(allp, f, indent=1)
        return {"ok": True, "stored": "studio/video-picks.json",
                "picks_learned": bool(title or voice_map)}
    with open(p, encoding="utf-8") as f:
        item = json.load(f)
    if title:
        item["title_pick"] = title[:120]
    if thumb_path:
        item["thumb_pick"] = thumb_path[:200]
    if voice_map:
        item["voice_map"] = {str(k)[:40]: str(v)[:40]
                             for k, v in list(voice_map.items())[:20]}
    if formula:
        item["title_formula"] = formula[:60]
    with open(p, "w", encoding="utf-8") as f:
        json.dump(item, f, indent=1)
    return {"ok": True, "stored": "bgraph item", "picks_learned": True}


# ---- episode assembly: etch clips + narration master → YT final ----
#
# Sleepdraw renders silent draw clips (CPU, sleepdraw venv for cv2);
# we concat, mux the bank master.mp3, and normalize to the YT spec
# (MEDIA-PIPELINE final-mux flags), then compliance-gate. Background
# job like renders (long CPU) — poll job_status.

SLEEPDRAW_VENV_PY = "/root/sleepdraw/.venv/bin/python"


def _etch_clip(art_path: str, outdir: str, knobs: dict) -> str:
    """One still → draw clip via sleepdraw venv (cv2 lives there)."""
    import subprocess as _sp
    code = (
        "import sys; sys.path.insert(0, '/root/sleepdraw');"
        "from sleepdraw import draw as _d;"
        f"_d.crop_169({art_path!r}, {os.path.join(outdir, 'crop.jpg')!r});"
        f"mp4, frames, log = _d.render({os.path.join(outdir, 'crop.jpg')!r},"
        f" {outdir!r}, {knobs!r}, duration_ms={int(knobs.get('dur', 30000))},"
        f" no_hand={bool(knobs.get('no_hand', True))});"
        "print('MP4:' + mp4)")
    r = _sp.run([SLEEPDRAW_VENV_PY, "-c", code], capture_output=True,
                text=True, timeout=3600)
    m = re.search(r"MP4:(\S+)", r.stdout or "")
    if not m or not os.path.isfile(m.group(1)):
        raise RuntimeError("etch failed: " + (r.stderr or r.stdout)[-500:])
    return m.group(1)


def _assemble(name: str, art_paths: list, audio_path: str,
              knobs: dict) -> dict:
    import subprocess as _sp
    if not art_paths:
        raise ValueError("no art supplied")
    if not os.path.isfile(audio_path):
        raise ValueError("narration master missing")
    workdir = os.path.join(REND, name + "-asm")
    os.makedirs(workdir, exist_ok=True)
    clips = []
    per = max(1, int(knobs.get("dur", 30000)))
    for i, art in enumerate(art_paths):
        cdir = os.path.join(workdir, f"clip{i:02d}")
        os.makedirs(cdir, exist_ok=True)
        full = art if os.path.isfile(art) else os.path.join(ART, art)
        if not os.path.isfile(full):
            raise ValueError(f"art missing: {art}")
        clips.append(_etch_clip(full, cdir, {**knobs, "dur": per}))
    lst = os.path.join(workdir, "clips.lst")
    with open(lst, "w") as f:
        for c in clips:
            f.write(f"file '{c}'\n")
    vcat = os.path.join(workdir, "video.mp4")
    _sp.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
             "-i", lst, "-c", "copy", vcat], check=True, timeout=600)
    final = os.path.join(workdir, name + "-final.mp4")
    _sp.run(["ffmpeg", "-y", "-v", "error", "-i", vcat, "-i", audio_path,
             "-vf", "scale=1920:1080,format=yuv420p",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
             "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
             "-shortest", "-movflags", "+faststart", final],
            check=True, timeout=1200)
    return {"mp4": f"/api/studio/file?kind=rend&dir={name}-asm&file="
                    f"{os.path.basename(final)}",
            "mp4path": final, "clips": len(clips), "knobs": knobs}


def start_assemble(name: str, art_paths: list, audio_path: str,
                   knobs: dict) -> str:
    jid = f"a{int(time.time())}"
    JOBS[jid] = {"status": "running", "name": name, "kind": "assemble"}

    def _t():
        try:
            JOBS[jid].update(_assemble(name, art_paths, audio_path, knobs))
            JOBS[jid]["status"] = "done"
        except Exception as e:  # noqa: BLE001
            JOBS[jid] = {"status": "error", "error": str(e)[-1000:]}

    threading.Thread(target=_t, daemon=True).start()
    return jid
