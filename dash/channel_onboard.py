"""Channel onboarding — thesis → pipeline → roles → voice choice.

Flow: pick a channel → see its thesis/pipeline/chairs → get 5 voice
candidates matched to the channel vibe WITH reasons → human picks with
a reason → lock writes the ID + reason into the channel record and
recompiles the seed. Later proposals learn from locked picks.

Voice matching (deterministic, no LLM): query terms from the chair
direction + channel pitch/shelf; rank by tag overlap, uses (social
proof), language; penalize voices already locked by sibling channels
(differentiation law). Reasons cite the actual evidence.
"""
from __future__ import annotations

import json
import math
import os
import sys as _sys
import time

# self-sufficient imports: works from server.py (dash on path), mcp.py
# (parent on path), and tests (either). No caller setup required.
_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (os.path.dirname(_HERE), os.path.join(os.path.dirname(_HERE), "pipeline")):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

from channel_character import load_channel, save_seed  # noqa: F401 (re-export)

_HERE = os.path.dirname(os.path.abspath(__file__))
CHANNELS_DIR = os.path.normpath(os.path.join(_HERE, "..", "studio", "channels"))

STOP = {"the", "a", "an", "and", "for", "with", "voice", "sleep", "calm",
        "male", "female", "use", "used", "uses", "own", "any", "its",
        "into", "from", "that", "this", "soft"}


def _audio_flow():
    sys_path_push()
    try:
        import audio_flow as _af
    except ImportError:
        from pipeline import audio_flow as _af
    return _af


def sys_path_push():
    import sys
    base = os.path.normpath(os.path.join(_HERE, ".."))
    if base not in sys.path:
        sys.path.insert(0, base)
    pipe = os.path.join(base, "pipeline")
    if pipe not in sys.path:
        sys.path.insert(0, pipe)


def _keywords(text: str) -> set[str]:
    import re
    words = re.findall(r"[a-z]{3,}", (text or "").lower())
    return {w for w in words if w not in STOP}


def vibe_queries(channel: dict, chair_name: str) -> list[str]:
    """2-3 Fish search queries from chair direction + channel pitch."""
    chairs = (channel.get("voice") or {}).get("chairs", {})
    chair = chairs.get(chair_name, {}) if isinstance(chairs, dict) else {}
    direction = chair.get("direction", "") or ""
    pitch = channel.get("pitch", "") or ""
    # NOTE: chair label excluded — it names the incumbent (e.g. Adrian)
    # and would bias search toward the status quo. Fresh ears each time.
    kws = sorted(_keywords(direction + " " + pitch))
    primary = " ".join(kws[:4]) or "calm narration"
    queries = [primary]
    _lbl = (chair.get("label", "") or "").lower()
    if "whisper" in direction.lower() or "whisper" in _lbl:
        queries.append("whisper soft spoken")
    if "female" in _lbl or "she " in direction.lower():
        queries.append("warm female narration")
    elif "male" in _lbl:
        queries.append("deep male narration")
    queries.append((channel.get("display_name", "") + " storytelling").strip())
    seen, out = set(), []
    for q in queries:
        if q and q not in seen:
            seen.add(q)
            out.append(q)
        if len(out) == 3:
            break
    return out


def _sibling_voice_ids(exclude_slug: str) -> set[str]:
    ids = set()
    if not os.path.isdir(CHANNELS_DIR):
        return ids
    for fn in os.listdir(CHANNELS_DIR):
        if not fn.endswith(".json") or fn[:-5] == exclude_slug:
            continue
        try:
            with open(os.path.join(CHANNELS_DIR, fn), encoding="utf-8") as f:
                rec = json.load(f)
            for c in ((rec.get("voice") or {}).get("chairs") or {}).values():
                if isinstance(c, dict):
                    if c.get("fish_id"):
                        ids.add(c["fish_id"])
                    for cand in c.get("candidates") or []:
                        if cand.get("id"):
                            ids.add(cand["id"])
        except Exception:
            continue
    return ids


def propose(channel_slug: str, chair: str = "narrator",
            n: int = 5, exclude: list | None = None) -> dict:
    """5 voice candidates matched to the channel vibe, each with samples
    and a reason citing tags/uses/language/differentiation. Free reads.
    exclude = voice IDs already seen (more-buttons, dismissed)."""
    af = _audio_flow()
    try:
        channel = load_channel(channel_slug)
    except OSError:
        return {"ok": False, "reason": f"unknown channel {channel_slug}"}
    chairs = (channel.get("voice") or {}).get("chairs", {})
    if chair not in chairs:
        return {"ok": False,
                "reason": f"no chair '{chair}' (have: {sorted(chairs)})"}
    chair_kw = _keywords((chairs[chair].get("direction", "") or "") + " " +
                         (chairs[chair].get("label", "") or ""))
    pool: dict[str, dict] = {}
    for q in vibe_queries(channel, chair):
        r = af.voices(q, "", False, 10)
        for v in ((r.get("data") or {}).get("voices") or []):
            vid = v.get("id") or v.get("voice_id", "")
            if vid and vid not in pool:
                pool[vid] = v
    siblings = _sibling_voice_ids(channel_slug)
    seen_ids = set(exclude or []) | _dismissed_ids(channel_slug)
    # incumbent always included for comparison (fresh challengers + status quo)
    incumbent = (chairs[chair].get("fish_id") or "")
    if incumbent and incumbent not in pool:
        d = af.voice_detail(incumbent).get("data") or {}
        if d.get("id") or d.get("voice_id"):
            pool[incumbent] = {"id": incumbent,
                               "title": d.get("title") or d.get("name"),
                               "languages": d.get("languages") or [],
                               "tags": d.get("tags") or [],
                               "sample_audio": d.get("sample_audio"),
                               "task_count": d.get("task_count") or 0}
    scored = []
    for vid, v in pool.items():
        if vid in seen_ids:
            continue
        tags = set((v.get("tags") or []))
        overlap = sorted({t for t in tags
                          if any(k in t for k in chair_kw)})
        uses = int(v.get("task_count") or 0)
        pop = min(10.0, math.log10(max(10, uses)))
        langs = v.get("languages") or v.get("language") or []
        if isinstance(langs, str):
            langs = [langs]
        lang_ok = any(str(l).startswith("en") for l in langs)
        shared = vid in siblings
        score = round(len(overlap) * 3 + pop + (2 if lang_ok else -5)
                      - (8 if shared else 0), 1)
        reasons = []
        if overlap:
            reasons.append(f"tags match vibe: {', '.join(overlap[:4])}")
        reasons.append(f"{uses:,} prior uses"
                       + (" (proven)" if uses > 20000 else " (niche)"))
        if not lang_ok:
            reasons.append("WARNING: not English-first")
        if shared:
            reasons.append("WARNING: locked by a sibling channel")
        if vid == incumbent:
            reasons.append("current lock — re-pick to keep, or dethrone")
            score = round(score + 0.5, 1)  # tie-break for the devil known
        scored.append({"voice_id": vid,
                       "name": v.get("title") or v.get("name"),
                       "language": langs[0] if langs else "?",
                       "tags": sorted(tags)[:8],
                       "sample": v.get("sample_audio"),
                       "uses": uses, "score": score,
                       "reason": "; ".join(reasons)})
    scored.sort(key=lambda c: c["score"], reverse=True)
    liked = _liked_ids(channel_slug, chair)
    return {"ok": True, "channel": channel_slug, "chair": chair,
            "queries": vibe_queries(channel, chair),
            "liked": sorted(liked),
            "candidates": scored[:n],
            "next": "human picks one with a reason → lock_voice writes it"}


def lock(channel_slug: str, chair: str, voice_id: str, reason: str,
         actor: str = "dash-human") -> dict:
    """Human-picked lock: writes fish_id + reason + timestamp into the
    channel record and recompiles the seed. Call ONLY from an
    authenticated human handler."""
    if not channel_slug.replace("-", "").replace("_", "").isalnum():
        return {"ok": False, "reason": "bad slug"}
    if not reason or not voice_id:
        return {"ok": False, "reason": "voice_id and human reason required"}
    path = os.path.join(CHANNELS_DIR, channel_slug + ".json")
    try:
        with open(path, encoding="utf-8") as f:
            rec = json.load(f)
    except OSError:
        return {"ok": False, "reason": f"unknown channel {channel_slug}"}
    chairs = (rec.get("voice") or {}).get("chairs", {})
    if chair not in chairs:
        return {"ok": False, "reason": f"no chair '{chair}'"}
    c = chairs[chair]
    c["fish_id"] = voice_id
    c["status"] = "locked"
    c["lock_reason"] = reason
    c["locked_by"] = actor
    c["locked_at"] = int(time.time())
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=1, ensure_ascii=False)
    os.replace(tmp, path)
    seed_path = save_seed(channel_slug)
    return {"ok": True, "channel": channel_slug, "chair": chair,
            "voice_id": voice_id, "seed": seed_path}


def locked_traits() -> list[dict]:
    """What the human has picked so far — new proposals learn from this."""
    out = []
    if not os.path.isdir(CHANNELS_DIR):
        return out
    for fn in sorted(os.listdir(CHANNELS_DIR)):
        if not fn.endswith(".json") or fn.endswith(".seed.json"):
            continue
        try:
            with open(os.path.join(CHANNELS_DIR, fn), encoding="utf-8") as f:
                rec = json.load(f)
            for name, c in (((rec.get("voice") or {}).get("chairs"))
                             or {}).items():
                if isinstance(c, dict) and c.get("fish_id"):
                    out.append({"channel": fn[:-5], "chair": name,
                                "label": c.get("label", ""),
                                "reason": c.get("lock_reason", "")})
        except Exception:
            continue
    return out


# ---- interactive channel config (brand identity, styles, thumbnails, formats)

# Allowlisted editable fields. Voices lock via lock() (with reason), never
# here. Engine/pipeline are code-owned; everything presentational is human.
CONFIG_TEXT = ("display_name", "pitch", "cadence")
CONFIG_STYLE = ("accent", "manner", "visual", "shelf")
CONFIG_THUMB = ("type", "rules")


def get_config(slug: str) -> dict:
    from channel_character import load_channel
    try:
        rec = load_channel(slug)
    except OSError:
        return {"ok": False, "reason": f"unknown channel {slug}"}
    return {"ok": True, "record": rec}


def save_config(slug: str, patch: dict) -> dict:
    """Human-owned presentational config. Allowlisted keys only; unknown
    keys ignored (never silently stored). Returns the updated record."""
    from channel_character import load_channel
    if (not slug.replace("-", "").replace("_", "").isalnum()
            or not isinstance(patch, dict)):
        return {"ok": False, "reason": "bad slug or patch"}
    try:
        rec = load_channel(slug)
    except OSError:
        return {"ok": False, "reason": f"unknown channel {slug}"}
    applied = []
    for k in CONFIG_TEXT:
        if isinstance(patch.get(k), str) and patch[k].strip():
            rec[k] = patch[k].strip()[:300]
            applied.append(k)
    if isinstance(patch.get("style"), dict):
        rec.setdefault("style", {})
        for k in CONFIG_STYLE:
            v = patch["style"].get(k)
            if isinstance(v, str) and v.strip():
                rec["style"][k] = v.strip()[:500]
                applied.append(f"style.{k}")
    if isinstance(patch.get("thumbnail"), dict):
        rec.setdefault("thumbnail", {})
        t = patch["thumbnail"]
        if isinstance(t.get("type"), str) and t["type"].strip():
            rec["thumbnail"]["type"] = t["type"].strip()[:300]
            applied.append("thumbnail.type")
        if isinstance(t.get("rules"), list):
            rec["thumbnail"]["rules"] = [str(r)[:200] for r in t["rules"][:12]]
            applied.append("thumbnail.rules")
    if isinstance(patch.get("formats"), list):
        fmts = []
        for f in patch["formats"][:20]:
            if not isinstance(f, dict):
                continue
            name = str(f.get("name", ""))[:80]
            if not name:
                continue
            fmts.append({"name": name,
                         "length": str(f.get("length", ""))[:40],
                         "reasoning": str(f.get("reasoning", ""))[:500]})
        rec["formats"] = fmts
        applied.append(f"formats[{len(fmts)}]")
    if not applied:
        return {"ok": False, "reason": "nothing allowlisted to save"}
    path = os.path.join(CHANNELS_DIR, slug + ".json")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=1, ensure_ascii=False)
    os.replace(tmp, path)
    return {"ok": True, "applied": applied, "record": rec}


def channel_status(slug: str) -> dict:
    """Per-entity answer seed for pi: record + chairs + bank + readiness.
    Free read. YT metrics attach once bgraph channel_id is claimed."""
    from channel_character import load_channel
    try:
        rec = load_channel(slug)
    except OSError:
        return {"ok": False, "reason": f"unknown channel {slug}"}
    import sleep_studio as _st
    bank = _st.list_voice_bank()
    chairs = (rec.get("voice") or {}).get("chairs", {})
    locked = [n for n, c in (chairs.items() if isinstance(chairs, dict) else [])
              if isinstance(c, dict) and c.get("fish_id")]
    open_chairs = [n for n in (chairs if isinstance(chairs, dict) else [])
                   if n not in locked]
    return {"ok": True, "slug": slug,
            "display_name": rec.get("display_name", slug),
            "status": rec.get("status", "pilot"),
            "pitch": rec.get("pitch", ""),
            "engine": (rec.get("engine") or {}).get("primary", ""),
            "cadence": rec.get("cadence", ""),
            "chairs_total": len(chairs), "chairs_locked": locked,
            "chairs_open": open_chairs,
            "brief": bool(os.path.isfile(
                os.path.join(CHANNELS_DIR, slug + "-brief.md"))),
            "bank_clips": len(bank),
            "formats": [f.get("name", "") for f in rec.get("formats", [])],
            "youtube": {"channel_id": None, "metrics": "no uploads yet — "
                        "stats attach after first unlisted upload"},
            "next": ("onboard voices for: " + ", ".join(open_chairs)
                     if open_chairs else "all chairs locked — render pilots")}


# ---- taste: likes, dismissals, general feedback (trains future proposes)

def _taste_path(slug: str) -> str:
    return os.path.join(CHANNELS_DIR, slug + "-taste.json")


def _taste(slug: str) -> dict:
    try:
        with open(_taste_path(slug), encoding="utf-8") as f:
            d = json.load(f)
            return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _save_taste(slug: str, d: dict) -> None:
    if (not slug.replace("-", "").replace("_", "").isalnum()):
        raise ValueError("bad slug")
    tmp = _taste_path(slug) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
    os.replace(tmp, _taste_path(slug))


def _dismissed_ids(slug: str) -> set[str]:
    return set(_taste(slug).get("dismissed") or [])


def _liked_ids(slug: str, chair: str = "") -> set[str]:
    out = set()
    for lk in (_taste(slug).get("likes") or []):
        if isinstance(lk, dict) and (not chair or lk.get("chair") == chair):
            if lk.get("voice_id"):
                out.add(lk["voice_id"])
    return out


def react(channel: str, chair: str, voice_id: str, name: str = "",
          liked: bool | None = None, dismissed: bool = False,
          note: str = "") -> dict:
    """Tick (like), dismiss, and/or note on a voice card. All stored with
    timestamps; propose() auto-excludes dismissed; picks cite likes."""
    if (not channel.replace("-", "").replace("_", "").isalnum()
            or not voice_id):
        return {"ok": False, "reason": "bad channel or voice"}
    d = _taste(channel)
    d.setdefault("likes", [])
    d.setdefault("dismissed", [])
    d.setdefault("feedback", [])
    if dismissed and voice_id not in d["dismissed"]:
        d["dismissed"].append(voice_id)
    if liked is True and voice_id not in [l.get("voice_id") for l in d["likes"]]:
        d["likes"].append({"chair": chair, "voice_id": voice_id,
                           "name": name, "note": note.strip()[:300],
                           "ts": int(time.time())})
    if liked is False:
        d["likes"] = [l for l in d["likes"]
                      if l.get("voice_id") != voice_id]
    if note.strip() and liked is None and not dismissed:
        d["feedback"].append({"chair": chair, "voice_id": voice_id,
                              "text": note.strip()[:500],
                              "ts": int(time.time())})
    _save_taste(channel, d)
    return {"ok": True, "likes": len(d["likes"]),
            "dismissed": len(d["dismissed"])}
