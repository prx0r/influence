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
import re
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
    anchors = _anchors()
    anchor_vocab: dict[str, str] = {}  # tag/word -> anchor title
    for a in anchors:
        for t in (a.get("tags") or []) + (a.get("descriptors") or []):
            anchor_vocab.setdefault(str(t).lower(), a.get("title", "?"))
    # calibrated taste weights (taste_profile.json, compiled from locks /
    # likes / anchors / notes). Falls back to hand defaults when thin.
    try:
        sys_path_push()
        from taste_profile import weight_of as _taste_w
    except Exception:
        def _taste_w(f, default=0.5):
            return default
    # dedupe: same voice re-uploaded under new IDs (Zack D. Films x2).
    # Normalized name match → keep the highest-use copy. No dup cards.
    import re as _re
    def _norm_name(v):
        return _re.sub(r"[^a-z0-9]", "", str(v.get("title") or v.get("name") or "").lower())
    best = {}
    for vid, v in pool.items():
        if vid in seen_ids:
            continue
        nm = _norm_name(v)
        if not nm:
            continue
        uses = int(v.get("task_count") or 0)
        if nm not in best or uses > int(best[nm].get("task_count") or 0):
            best[nm] = v
    # incumbent always included for comparison (fresh challengers + status quo)
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
            nm = _norm_name(pool[incumbent])
            if nm and (nm not in best or int(pool[incumbent].get("task_count") or 0)
                       >= int(best[nm].get("task_count") or 0)):
                best[nm] = pool[incumbent]
    scored = []
    # function fit once per propose (not per candidate): which calibration
    # function this chair maps to + its fitted weights ({} = uncalibrated).
    try:
        sys_path_push()
        from taste_profile import chair_function as _cfn
        from taste_profile import function_weights as _fw
        _fn = _cfn(chair, " ".join(
            sorted(_keywords((chairs[chair].get("direction", "") or "")))))
        _fww = _fw(_fn)
    except Exception:
        _fn, _fww = "narration", {}
    for v in best.values():
        vid = v.get("id") or v.get("voice_id") or ""
        if not vid or vid in seen_ids:
            continue
        tags = set((v.get("tags") or []))
        overlap = sorted({t for t in tags
                          if any(k in t for k in chair_kw)},
                         key=lambda t: (-len(t), t))
        uses = int(v.get("task_count") or 0)
        pop = min(10.0, math.log10(max(10, uses)))
        langs = v.get("languages") or v.get("language") or []
        if isinstance(langs, str):
            langs = [langs]
        lang_ok = any(str(l).startswith("en") for l in langs)
        shared = vid in siblings
        # calibrated overlap: learned weight per tag, modulated around the
        # old +3 default (w=1 → 3.0, w=-1 → 0). Unknown tags → neutral.
        overlap_score = round(sum(1.5 + 1.5 * _taste_w(t, 0.5)
                                  for t in overlap)
                              + sum(_fww.get(t.lower(), 0.0) * 2.0
                                    for t in tags), 1)
        score = round(overlap_score + pop + (2 if lang_ok else -5)
                      - (8 if shared else 0), 1)
        reasons = []
        if overlap:
            if len(overlap) == 1 and len(overlap[0]) <= 5:
                reasons.append(f"weak tag match ({overlap[0]}) — judge the sample")
            else:
                reasons.append(f"tags match vibe: {', '.join(overlap[:4])}")
        anchor_hit = sorted({t for t in tags if t.lower() in anchor_vocab},
                            key=lambda t: (-len(t), t))
        if not overlap and not anchor_hit:
            reasons.append("no tag overlap — sample decides")
        if anchor_hit:
            cited = sorted({anchor_vocab[t.lower()] for t in anchor_hit})
            reasons.append(f"owner taste ({', '.join(cited[:2])}): "
                           f"{', '.join(anchor_hit[:4])}")
            score = round(score + min(4.0, 2.0 * len(anchor_hit)), 1)
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
            "function": _fn,
            "function_calibrated": bool(_fww),
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
    # recompile taste profile (cheap, keeps ranking calibrated)
    try:
        sys_path_push()
        from taste_profile import compile_profile as _compile
        _compile()
    except Exception:
        pass
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
    if isinstance(patch.get("series"), list):
        # Series edits: narrator + characters + thumbnail override only.
        # Structure (id/videos/collections) is migration-owned, never edited.
        by_id = {s.get("id"): s for s in rec.get("series", [])
                 if isinstance(s, dict)}
        touched = 0
        for s in patch["series"][:20]:
            if not isinstance(s, dict) or s.get("id") not in by_id:
                continue
            cur = by_id[s["id"]]
            if isinstance(s.get("narrator"), dict):
                nv = str(s["narrator"].get("voice_id", ""))[:40]
                if nv and re.fullmatch(r"[0-9a-f]{32}", nv):
                    cur["narrator"] = {
                        "voice_id": nv,
                        "label": str(s["narrator"].get("label", ""))[:120],
                        "status": "locked",
                        "lock_reason": str(
                            s["narrator"].get("reason", ""))[:300]}
                    touched += 1
            if isinstance(s.get("characters"), dict):
                chars = cur.setdefault("characters", {})
                for nm, vid in list(s["characters"].items())[:30]:
                    if (isinstance(nm, str) and isinstance(vid, str)
                            and re.fullmatch(r"[0-9a-f]{32}", vid)):
                        chars[nm[:60]] = vid
                        touched += 1
            if isinstance(s.get("thumbnail"), dict):
                cur["thumbnail"] = {
                    "inherit": False,
                    "type": str(s["thumbnail"].get("type", ""))[:300],
                    "rules": [str(r)[:200]
                              for r in s["thumbnail"].get("rules", [])[:12]]}
                touched += 1
        if touched:
            applied.append(f"series[{touched}]")
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
    try:
        sys_path_push()
        from taste_profile import compile_profile as _compile2
        _compile2()
    except Exception:
        pass
    return {"ok": True, "likes": len(d["likes"]),
            "dismissed": len(d["dismissed"])}


# ---- loved-voice anchors (weight the recommender by owner taste)

ANCHORS_PATH = os.path.join(CHANNELS_DIR, "..", "voice-anchors.json")


def _anchors() -> list:
    try:
        with open(os.path.normpath(ANCHORS_PATH), encoding="utf-8") as f:
            d = json.load(f)
            return d if isinstance(d, list) else []
    except Exception:
        return []


def love(voice_id: str, descriptors: list, context: str = "",
         note: str = "") -> dict:
    """Anchor a loved voice: fetch its card, store tags + owner descriptors.
    propose() boosts candidates sharing anchor DNA and cites the anchor."""
    if not voice_id or not re.fullmatch(r"[0-9a-f]{32}", voice_id):
        return {"ok": False, "reason": "bad voice id"}
    af = _audio_flow()
    d = af.voice_detail(voice_id).get("data") or {}
    if not d.get("id"):
        return {"ok": False, "reason": "voice not found"}
    desc = [str(x).lower()[:40] for x in (descriptors or []) if str(x).strip()][:12]
    anchors = _anchors()
    anchors = [a for a in anchors if a.get("voice_id") != voice_id]
    anchors.append({"voice_id": voice_id,
                    "title": d.get("title") or "",
                    "tags": d.get("tags") or [],
                    "languages": d.get("languages") or [],
                    "descriptors": desc, "context": context[:120],
                    "note": note[:300], "ts": int(time.time())})
    tmp = os.path.normpath(ANCHORS_PATH) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(anchors, f, indent=1, ensure_ascii=False)
    os.replace(tmp, os.path.normpath(ANCHORS_PATH))
    try:
        sys_path_push()
        from taste_profile import compile_profile as _compile3
        _compile3()
    except Exception:
        pass
    return {"ok": True, "title": d.get("title"),
            "tags": d.get("tags"), "anchors": len(anchors)}


# ---- prompt-to-voice engine: anchors → voice-design instruction ----
#
# The owner sends voices they love with descriptors. This compiles them
# into a voice-design prompt: anchor tags + owner words + purpose, so
# Fish generates new voices in the taste we've demonstrated, not random.
# Generation itself ($0.01) stays behind explicit approval (studio UI
# confirm dialog / design_voice approved=True).

_GENERIC_TAGS = {"male", "female", "young", "middle-aged", "old",
                 "character-voice", "entertainment", "english"}


def anchor_prompt(purpose: str, voice_ids: list | None = None,
                  max_anchors: int = 4) -> dict:
    """Compile loved voices into a voice-design instruction. Pure, $0."""
    anchors = _anchors()
    if voice_ids:
        wanted = set(voice_ids)
        anchors = [a for a in anchors if a.get("voice_id") in wanted]
    if not anchors:
        return {"ok": False, "reason": "no anchors (love some voices first)"}
    anchors = anchors[-max_anchors:]
    quals: list = []
    seen: set = set()
    for a in anchors:
        for t in (a.get("tags") or []) + (a.get("descriptors") or []):
            t = str(t).strip()
            if t and t.lower() not in _GENERIC_TAGS and t.lower() not in seen:
                seen.add(t.lower())
                quals.append(t)
    names = ", ".join(a.get("title", "?") for a in anchors)
    instruction = (f"A voice combining {', '.join(quals[:14])}. "
                   f"In the spirit of {names}. For {purpose}.")
    return {"ok": True, "instruction": instruction[:1800],
            "sources": [a.get("title") for a in anchors],
            "purpose": purpose,
            "next": "approve $0.01 to generate candidates via design_voice"}


def react_thumb(channel: str, thumb_ref: str, liked: bool,
                note: str = "") -> dict:
    """Tick/dismiss a thumbnail (+ optional style note like 'dark, no faces').
    Stored with timestamps; compiled into taste profile lane rules."""
    if (not channel.replace("-", "").replace("_", "").isalnum()
            or not thumb_ref):
        return {"ok": False, "reason": "bad channel or thumb"}
    d = _taste(channel)
    d.setdefault("thumb_likes", [])
    d.setdefault("thumb_dismissed", [])
    d.setdefault("feedback", [])
    if liked and thumb_ref not in [t.get("ref") for t in d["thumb_likes"]]:
        d["thumb_likes"].append({"ref": thumb_ref[:200],
                                 "note": note.strip()[:300],
                                 "ts": int(time.time())})
    if not liked and thumb_ref not in d["thumb_dismissed"]:
        d["thumb_dismissed"].append(thumb_ref[:200])
    if note.strip():
        d["feedback"].append({"chair": "thumbnail", "voice_id": "",
                              "text": note.strip()[:500],
                              "ts": int(time.time())})
    _save_taste(channel, d)
    try:
        sys_path_push()
        from taste_profile import compile_profile as _compile4
        _compile4()
    except Exception:
        pass
    return {"ok": True, "thumb_likes": len(d["thumb_likes"])}
