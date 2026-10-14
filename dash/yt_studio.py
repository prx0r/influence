"""YT studio loop (youtube.agentcom.org P0): pick channel → hear a pilot
preview → tell Pi "more like this" → re-take → "ok render full" → store
the formula and reuse it.

Everything here is $0: previews and full renders go through
sleep_studio.render_pilot (REST free tier). No grants, no credits.
Renders run in background threads (a full episode can outlive the
Cloudflare 100s request limit); the UI polls job().

Formula = the knobs that produced the take you liked, stored per channel
at studio/channels/<slug>.formula.json. Next pilot on that channel starts
from it.
"""
from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
import uuid

ROOT = os.path.dirname(os.path.abspath(__file__))
CHAN_DIR = os.path.normpath(os.path.join(ROOT, "..", "studio", "channels"))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

JOBS: dict = {}
_LOCK = threading.Lock()

DEFAULT_KNOBS = {"speed": None, "temperature": 0.7, "volume_db": 0.0,
                 "preview_segments": 4, "voices": {}}


def _ok_slug(slug: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9_-]{1,64}", slug or ""))


def _record(slug: str) -> dict:
    if not _ok_slug(slug):
        raise ValueError("bad slug")
    with open(os.path.join(CHAN_DIR, slug + ".json"), encoding="utf-8") as f:
        return json.load(f)


# ---- formula --------------------------------------------------------------

def formula_path(slug: str) -> str:
    if not _ok_slug(slug):
        raise ValueError("bad slug")
    return os.path.join(CHAN_DIR, slug + ".formula.json")


def load_formula(slug: str) -> dict:
    try:
        with open(formula_path(slug), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def clean_knobs(k: dict | None, rec: dict | None = None) -> dict:
    """Clamp + allowlist. Anything unknown is dropped, never stored."""
    k = k if isinstance(k, dict) else {}
    out = dict(DEFAULT_KNOBS, voices={})
    pace = ((rec or {}).get("voice") or {}).get("pace")
    sp = k.get("speed", pace)
    out["speed"] = (round(max(0.5, min(2.0, float(sp))), 2)
                    if isinstance(sp, (int, float)) else None)
    t = k.get("temperature", out["temperature"])
    if isinstance(t, (int, float)):
        out["temperature"] = round(max(0.0, min(1.0, float(t))), 2)
    v = k.get("volume_db", 0.0)
    if isinstance(v, (int, float)):
        out["volume_db"] = round(max(-12.0, min(6.0, float(v))), 1)
    n = k.get("preview_segments", out["preview_segments"])
    if isinstance(n, (int, float)):
        out["preview_segments"] = int(max(1, min(40, n)))
    vs = k.get("voices") or {}
    if isinstance(vs, dict):
        for chair, vid in list(vs.items())[:12]:
            if (isinstance(chair, str) and isinstance(vid, str)
                    and re.fullmatch(r"[0-9a-f]{32}", vid)
                    and re.fullmatch(r"[A-Za-z0-9_-]{1,40}", chair)):
                out["voices"][chair] = vid
    return out


def save_formula(slug: str, knobs: dict, take: str = "", note: str = "",
                 titles: list | None = None) -> dict:
    rec = _record(slug)
    cur = load_formula(slug)
    f = {"channel": slug, "knobs": clean_knobs(knobs, rec),
         "from_take": os.path.basename(take or "")[:120],
         "note": (note or "")[:500],
         "titles": [str(t)[:140] for t in (titles if titles is not None
                                            else cur.get("titles", []))][:20],
         "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
         "version": int(cur.get("version", 0)) + 1}
    hist = (cur.get("history") or [])[-9:]
    if cur.get("knobs"):
        hist.append({k: cur.get(k) for k in
                     ("knobs", "from_take", "note", "saved_at", "version")})
    f["history"] = hist
    with open(formula_path(slug), "w", encoding="utf-8") as fh:
        json.dump(f, fh, indent=1)
    return {"ok": True, "formula": f}


# ---- channel view ---------------------------------------------------------

def _chairs(rec: dict) -> list:
    out = []
    for name, c in (((rec.get("voice") or {}).get("chairs")) or {}).items():
        if not isinstance(c, dict):
            continue
        opts = []
        if c.get("fish_id"):
            opts.append({"id": c["fish_id"], "label": c.get("label") or name,
                         "locked": True})
        for cand in c.get("candidates") or []:
            if isinstance(cand, dict) and cand.get("id") and cand["id"] not in [
                    o["id"] for o in opts]:
                opts.append({"id": cand["id"],
                             "label": cand.get("label") or cand["id"][:6],
                             "locked": False})
        out.append({"name": name, "direction": c.get("direction", ""),
                    "status": c.get("status", ""),
                    "locked": bool(c.get("fish_id")), "options": opts})
    return out


def channel_view(slug: str) -> dict:
    import sleep_studio as st
    rec = _record(slug)
    try:
        pilots = st.list_pilots()
    except Exception:  # damn tree missing on this box
        pilots = []
    mine = [p for p in pilots if p.get("house") == slug]
    takes = [c for c in st.list_voice_bank()
             if c.get("channel") == slug
             or (c.get("pilot") or {}).get("channel") == slug]
    return {"ok": True, "slug": slug,
            "name": rec.get("display_name", slug),
            "status": rec.get("status", ""), "pitch": rec.get("pitch", ""),
            "cadence": rec.get("cadence", ""),
            "accent": (rec.get("style") or {}).get("accent", ""),
            "style": rec.get("style") or {},
            "thumbnail": rec.get("thumbnail") or {},
            "formats": rec.get("formats") or [],
            "pace": (rec.get("voice") or {}).get("pace"),
            "bed": (rec.get("voice") or {}).get("bed", ""),
            "chairs": _chairs(rec),
            "pilots": mine,
            "other_pilots": [p for p in pilots if p.get("house") != slug],
            "takes": takes[:40],
            "formula": load_formula(slug)}


def channels() -> list:
    import sleep_studio as st
    out = []
    for c in st.list_channels():
        rec = {}
        try:
            rec = _record(c["slug"])
        except Exception:
            pass
        out.append({"slug": c["slug"], "name": c["display_name"],
                    "status": c.get("status", ""),
                    "accent": (rec.get("style") or {}).get("accent", ""),
                    "chairs": c.get("chairs", 0),
                    "chairs_locked": c.get("chairs_locked", 0),
                    "formula": bool(load_formula(c["slug"]))})
    return out


# ---- renders (async) ------------------------------------------------------

def start_take(path: str, slug: str, knobs: dict, full: bool = False,
               note: str = "") -> dict:
    import sleep_studio as st
    rec = _record(slug)
    k = clean_knobs(knobs, rec)
    st.parse_drama(path)  # path guard + existence, raises early
    jid = uuid.uuid4().hex[:10]
    job = {"id": jid, "status": "running", "full": bool(full),
           "channel": slug, "pilot": os.path.basename(path),
           "knobs": k, "note": note[:300], "started": time.time()}
    with _LOCK:
        JOBS[jid] = job
        # keep the table small
        for old in sorted(JOBS, key=lambda j: JOBS[j]["started"])[:-50]:
            JOBS.pop(old, None)

    def run():
        try:
            r = st.render_pilot(
                path, slug, voice_overrides=k["voices"] or None,
                speed=k["speed"], temperature=k["temperature"],
                volume_db=k["volume_db"],
                max_segments=0 if full else k["preview_segments"],
                tag_prefix=("full" if full else "take"),
                extra_meta={"channel": slug, "knobs": k,
                            "take_kind": "full" if full else "preview",
                            "pilot_file": os.path.basename(path),
                            "note": note[:300],
                            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                time.gmtime())})
        except Exception as e:  # noqa: BLE001 — job reports, never raises
            r = {"ok": False, "reason": str(e)[:300]}
        with _LOCK:
            job.update(status="done" if r.get("ok") else "failed",
                       result=r, finished=time.time())

    threading.Thread(target=run, daemon=True).start()
    return {"ok": True, "job": jid, "knobs": k}


def job(jid: str) -> dict:
    with _LOCK:
        j = JOBS.get(str(jid))
        return dict(j) if j else {"status": "unknown"}


# ---- vibe: "more like this" → knobs --------------------------------------

_FULL = re.compile(r"\b(render (the )?full|full (render|video|episode|audio)|"
                   r"ok,? render|go full|do the (whole|full))\b", re.I)
_SAVE = re.compile(r"\b(save|lock|store|keep)\b.*\b(formula|recipe|this|it)\b"
                   r"|\bthat'?s the (vibe|one)\b", re.I)
_LISTEN = re.compile(r"\b(play|preview|again|retake|re-?render|try)\b", re.I)


def rule_vibe(note: str, knobs: dict, chairs: list) -> dict:
    """Deterministic fallback when the model is down. Small, legible steps."""
    n = (note or "").lower()
    k = json.loads(json.dumps(knobs))
    sp = k.get("speed") or 1.0
    t = k.get("temperature") if k.get("temperature") is not None else 0.7
    said = []
    if _FULL.search(n):
        return {"intent": "render_full", "knobs": k,
                "reply": "Rendering the full pilot with these knobs ($0)."}
    if _SAVE.search(n):
        return {"intent": "save_formula", "knobs": k,
                "reply": "Saved as this channel's formula."}
    if re.search(r"\b(slower|slow (it )?down|more relaxed|sleepier|drowsier)\b", n):
        sp -= 0.06
        said.append("slower")
    if re.search(r"\b(faster|speed (it )?up|too slow|pick up)\b", n):
        sp += 0.06
        said.append("faster")
    if re.search(r"\b(calmer|flatter|steadier|less dramatic|softer|gentler|whisper)", n):
        t -= 0.15
        said.append("steadier delivery")
    if re.search(r"\b(more (expressive|dramatic|emotion|alive|life)|livelier|warmer)", n):
        t += 0.15
        said.append("more expressive")
    if re.search(r"\b(louder|more volume)\b", n):
        k["volume_db"] = (k.get("volume_db") or 0) + 1.5
        said.append("louder")
    if re.search(r"\b(quieter|lower volume)\b", n):
        k["volume_db"] = (k.get("volume_db") or 0) - 1.5
        said.append("quieter")
    m = re.search(r"\b(longer|shorter) (preview|sample|clip)", n)
    if m:
        cur = int(k.get("preview_segments") or 4)
        k["preview_segments"] = cur + 3 if m.group(1) == "longer" else max(1, cur - 2)
        said.append(f"{m.group(1)} preview")
    for ch in chairs:
        for o in ch.get("options", []):
            first = (o.get("label") or "").split()[0].lower()
            if first and len(first) > 2 and re.search(rf"\b{re.escape(first)}\b", n):
                k.setdefault("voices", {})[ch["name"]] = o["id"]
                said.append(f"{ch['name']} → {o['label']}")
    k["speed"] = round(max(0.5, min(2.0, sp)), 2)
    k["temperature"] = round(max(0.0, min(1.0, t)), 2)
    if said:
        return {"intent": "retake", "knobs": k,
                "reply": "Retaking: " + ", ".join(said) + "."}
    if _LISTEN.search(n):
        return {"intent": "retake", "knobs": k, "reply": "Retaking as is."}
    return {"intent": "chat", "knobs": knobs, "reply": ""}


VIBE_SYSTEM = """You tune a $0 TTS render for a sleep YouTube channel.
The human just heard a preview take and gives direction in plain words.
Map it to knobs and reply ONLY with JSON:
{"intent": "retake"|"render_full"|"save_formula"|"chat",
 "knobs": {"speed": 0.5-2.0, "temperature": 0-1, "volume_db": -12..6,
           "preview_segments": 1-40, "voices": {"<chair>": "<voice id>"}},
 "reply": "one short sentence saying what you changed and why"}
Rules: speed is pace (sleep sits ~0.72-0.9). temperature is expressiveness
(lower = steadier, higher = more alive). Only use voice ids from the chair
options given. Small steps (speed ±0.03-0.08, temperature ±0.1-0.2).
"render full"/"ok go"/"that's it, do the whole thing" = render_full.
"save/lock this formula" = save_formula. Questions or anything not about
the sound = chat (knobs unchanged, reply empty)."""


def vibe(slug: str, note: str, knobs: dict, pilot: str = "",
         history: list | None = None) -> dict:
    rec = _record(slug)
    k = clean_knobs(knobs, rec)
    chairs = _chairs(rec)
    # tight intents never need the model
    if _FULL.search(note or "") or _SAVE.search(note or ""):
        return {"ok": True, "mode": "rules", **rule_vibe(note, k, chairs)}
    try:
        from agent_chat import _call_llm  # type: ignore
    except Exception:
        try:
            from dash.agent_chat import _call_llm
        except Exception:
            _call_llm = None
    if _call_llm is not None:
        try:
            ctx = {"channel": rec.get("display_name", slug),
                   "pitch": rec.get("pitch", ""),
                   "pilot": os.path.basename(pilot or ""),
                   "current_knobs": k,
                   "chairs": [{"chair": c["name"], "direction": c["direction"],
                               "options": [{"id": o["id"], "label": o["label"]}
                                           for o in c["options"]]}
                              for c in chairs]}
            msgs = [{"role": "system", "content": VIBE_SYSTEM},
                    {"role": "user", "content":
                     "CONTEXT " + json.dumps(ctx) + "\nDIRECTION: " + note}]
            out = _call_llm(msgs)
            txt = (out.get("content") or "").strip()
            m = re.search(r"\{.*\}", txt, re.S)
            data = json.loads(m.group(0)) if m else {}
            intent = data.get("intent")
            if intent in ("retake", "render_full", "save_formula", "chat"):
                merged = dict(k)
                nk = data.get("knobs") or {}
                if isinstance(nk, dict):
                    merged.update({x: nk[x] for x in nk if x in DEFAULT_KNOBS})
                    if isinstance(nk.get("voices"), dict):
                        allowed = {o["id"] for c in chairs for o in c["options"]}
                        merged["voices"] = dict(k["voices"], **{
                            ch: v for ch, v in nk["voices"].items()
                            if v in allowed})
                return {"ok": True, "mode": "model", "intent": intent,
                        "knobs": clean_knobs(merged, rec),
                        "reply": str(data.get("reply") or "")[:400]}
        except Exception:
            pass
    return {"ok": True, "mode": "rules", **rule_vibe(note, k, chairs)}
