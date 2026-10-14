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


def _keywords_ordered(text: str) -> list[str]:
    """Keywords in encounter order (brief words outrank pitch words)."""
    out = []
    for w in re.findall(r"[a-z]{3,}", (text or "").lower()):
        if w not in STOP and w not in out:
            out.append(w)
    return out


def vibe_queries(channel: dict, chair_name: str) -> list[str]:
    """2-3 Fish search queries from chair direction + channel pitch."""
    chairs = (channel.get("voice") or {}).get("chairs", {})
    chair = chairs.get(chair_name, {}) if isinstance(chairs, dict) else {}
    direction = chair.get("direction", "") or ""
    pitch = channel.get("pitch", "") or ""
    # NOTE: chair label excluded — it names the incumbent (e.g. Adrian)
    # and would bias search toward the status quo. Fresh ears each time.
    # Brief leads: direction words in encounter order first, channel pitch
    # only fills leftover slots (pitch is visual style words — "etch fairy
    # fairytales" must never BE the query for a ghost tale).
    dkws = _keywords_ordered(direction)
    pkws = [w for w in _keywords_ordered(pitch) if w not in dkws]
    primary = " ".join((dkws + pkws)[:4]) or "calm narration"
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
            n: int = 5, exclude: list | None = None,
            direction: str = "", voice_profile: dict | None = None,
            collection: str = "") -> dict:
    """5 voice candidates matched to the channel vibe, each with samples
    and a reason citing tags/uses/language/differentiation. Free reads.
    exclude = voice IDs already seen (more-buttons, dismissed).
    direction = ad-hoc chair brief (calibration studio: any character).
    voice_profile = mapped character delivery-spec (character_to_voice):
    its voice_words join the match set, and it is returned for display.
    collection = collection slug (folk-and-fable): the collection's vibe,
    tradition and narrator prediction lead the brief — a kwaidan narrator
    and an anansi narrator must never be the same search."""
    af = _audio_flow()
    try:
        channel = load_channel(channel_slug)
    except OSError:
        if not direction:
            return {"ok": False, "reason": f"unknown channel {channel_slug}"}
        # generic room: any character profile can be cast without a channel
        # (packs, one-offs, cross-lane work). No pitch, no siblings.
        channel = {"channel": channel_slug, "display_name": channel_slug,
                   "pitch": "", "voice": {"chairs": {}}}
        _generic = True
    else:
        _generic = False
    chairs = (channel.get("voice") or {}).get("chairs", {})
    if chair not in chairs:
        if not direction:
            return {"ok": False,
                    "reason": f"no chair '{chair}' (have: {sorted(chairs)})"}
        chairs = dict(chairs)
        chairs[chair] = {"direction": direction, "label": chair,
                         "status": "ad-hoc"}
    chair_kw = _keywords((chairs[chair].get("direction", "") or "") + " " +
                         (chairs[chair].get("label", "") or ""))
    # ad-hoc brief always counts: for existing chairs the passed direction
    # otherwise dies silently (queries were built from channel pitch while
    # the ghost-tale brief sat unused). Merge its words + lead query.
    _dir_kw = _keywords(direction) if direction else set()
    chair_kw |= _dir_kw
    # collection context (folk-and-fable theses): vibe + tradition +
    # narrator prediction lead the brief. Cached per process.
    _coll = None
    if collection:
        try:
            sys_path_push()
            import time as _t
            _th_path = os.path.join(os.path.dirname(CHANNELS_DIR),
                                    "voice-thesis", channel_slug + ".json")
            _th_mtime = os.path.getmtime(_th_path)
            if not hasattr(propose, "_th_cache") or \
                    getattr(propose, "_th_mtime", 0) != _th_mtime:
                propose._th_cache = json.load(open(_th_path, encoding="utf-8"))
                propose._th_mtime = _th_mtime
            for _c in (propose._th_cache.get("collections") or []):
                if _c.get("collection") == collection:
                    _coll = _c
                    break
        except Exception:
            _coll = None
    if _coll:
        _ctext = " ".join([
            _coll.get("tradition", ""),
            " ".join(v.get("vibe", "") for v in _coll.get("vibes", [])),
            ((_coll.get("narrator") or {}).get("voice", "")),
            ((_coll.get("narrator") or {}).get("why", ""))[:200],
        ])
        for _w in _keywords_ordered(_ctext)[:14]:
            if len(_w) >= 3:
                chair_kw.add(_w)
    # archetype vocabulary (research gets close): classify the chair,
    # add its delivery words to the match set. Taste narrows within.
    _arch, _arch_prof = "", {}
    try:
        sys_path_push()
        from ensemble_cast import classify_archetype as _cla
        _ar = _cla(chair + " " + (chairs[chair].get("direction", "") or "") +
                  " " + (direction or "") +
                  " " + ((_coll or {}).get("tradition", "") or "") +
                  " " + " ".join(v.get("vibe", "")
                                  for v in ((_coll or {}).get("vibes", []) or [])) +
                  " " + (((_coll or {}).get("narrator") or {}).get("voice", "") or ""),
                  (chairs[chair].get("direction", "") or "") + " " + (direction or ""))
        if _ar.get("confidence", 0) > 0:
            _arch, _arch_prof = _ar["archetype"], _ar["profile"]
            chair_kw |= _keywords(_arch_prof.get("delivery", "") or "")
    except Exception:
        pass
    # theory tags: what a voice OF the predicted archetype is tagged by
    # vendors. Scored as its own term so the prediction carries points.
    _arch_tags: set = set()
    if _arch:
        try:
            sys_path_push()
            from ensemble_cast import ARCHETYPE_TAGS as _ATT
            _arch_tags = set(_ATT.get(_arch, ()))
        except Exception:
            pass
    _vp = voice_profile
    if isinstance(_vp, dict) and "voice_profile" in _vp and isinstance(
            _vp.get("voice_profile"), dict):
        _vp = _vp["voice_profile"]
    if not isinstance(_vp, dict):
        _vp = None
    if _vp:
        for _w in _vp.get("voice_words", []) or []:
            _w = "".join(c for c in str(_w).lower() if c.isalpha())
            if len(_w) >= 3 and _w not in STOP:
                chair_kw.add(_w)
    # character graph (book truth): species queries shrink the pool before
    # scoring; vetoes penalize contradictions. Ad-hoc/pack chairs have no
    # dramatis and skip this cleanly (None).
    _cg = None
    try:
        sys_path_push()
        from character_graph import build as _cgbuild
        _cg = _cgbuild(channel_slug, chair)
    except Exception:
        _cg = None
    _vetoes: set = set((_cg or {}).get("vetoes", []) or [])
    _queries = list((_cg or {}).get("queries", []) or []) or None
    if _cg:
        for _qw in " ".join(_cg.get("queries", [])).lower().split():
            _qw = "".join(c for c in _qw if c.isalpha())
            if len(_qw) >= 4 and _qw not in STOP:
                chair_kw.add(_qw)
    _NARRATOR_CHAIRS = {"narrator", "monk", "lecturer", "anchor",
                        "loremaster", "guide", "companion", "documentarian",
                        "clinician", "foreman", "imaginal", "guest", "crew",
                        "ground", "mommy"}
    # role: narrator (carries long passages warmly) vs character (persona
    # over carrier). Without this, narrator and tortoise briefs spend the
    # same vendor words and crown the same voices out of a 30-voice pool.
    _is_narrator = chair.strip().lower() in _NARRATOR_CHAIRS
    pool: dict[str, dict] = {}
    # graph queries narrow (species truth), vibe queries widen (recall),
    # ad-hoc brief leads (explicit instruction beats channel default);
    # unioned so "tiger" finds tortoise-slow voices AND narration voices.
    _lead = [" ".join(_keywords_ordered(direction)[:6])] if _dir_kw else []
    if _coll:
        _cth = " ".join([
            ((_coll.get("narrator") or {}).get("voice", "")),
            _coll.get("tradition", ""),
            " ".join(v.get("vibe", "") for v in _coll.get("vibes", [])),
        ])
        _lead = [" ".join(_keywords_ordered(_cth)[:6])] + _lead
    _all_q = list(dict.fromkeys(
        _lead + list(_queries or []) + vibe_queries(channel, chair)))
    for q in _all_q:
        r = af.voices(q, "", False, 15)
        for v in ((r.get("data") or {}).get("voices") or []):
            vid = v.get("id") or v.get("voice_id", "")
            if vid and vid not in pool:
                pool[vid] = v
    siblings = _sibling_voice_ids(channel_slug)
    seen_ids = set(exclude or []) | _dismissed_ids(channel_slug)
    anchors = _anchors()
    anchor_vocab: dict[str, str] = {}  # tag/word -> anchor title
    anchor_src: dict[str, str] = {}  # tag/word -> anchor voice_id
    for a in anchors:
        for t in (a.get("tags") or []) + (a.get("descriptors") or []):
            anchor_vocab.setdefault(str(t).lower(), a.get("title", "?"))
            anchor_src.setdefault(str(t).lower(), str(a.get("voice_id") or ""))
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
    incumbent = (chairs[chair].get("fish_id") or "")
    # measured acoustics cache (studio/voice-acoustics.json): sleep-fit
    # from waveforms, not tags. Tags lie; measurements don't (sample-scoped).
    try:
        with open(os.path.join(os.path.dirname(CHANNELS_DIR),
                               "voice-acoustics.json"),
                  encoding="utf-8") as _af:
            import json as _js2
            _ac = _js2.load(_af)
            _ac = _ac if isinstance(_ac, dict) else {}
    except Exception:
        _ac = {}
    if incumbent and incumbent not in pool:
        d = af.voice_detail(incumbent).get("data") or {}
        if d.get("id") or d.get("voice_id"):
            pool[incumbent] = {"id": incumbent,
                               "title": d.get("title") or d.get("name"),
                               "languages": d.get("languages") or [],
                               "tags": d.get("tags") or [],
                               "sample_audio": d.get("sample_audio") or (
                                   d.get("sample") or {}).get("audio", ""),
                               "task_count": d.get("task_count") or 0}
            nm = _norm_name(pool[incumbent])
            if nm and (nm not in best or int(pool[incumbent].get("task_count") or 0)
                       >= int(best[nm].get("task_count") or 0)):
                best[nm] = pool[incumbent]
    # loved voices always included (owner taste anchors — Calm Sleep
    # Narrator, Sleepy, Luna…): English-first, marked so reasons cite them.
    for _a in _anchors():
        _vid = str(_a.get("voice_id") or "")
        _langs = _a.get("languages") or ["en"]
        if not _vid or _vid in pool:
            continue
        if not any(str(_l).startswith("en") for _l in _langs):
            continue
        pool[_vid] = {"id": _vid, "title": _a.get("title") or "loved voice",
                      "languages": _langs, "tags": _a.get("tags") or [],
                      "sample_audio": _a.get("sample_audio"),
                      "task_count": _a.get("task_count") or 0,
                      "_anchor": _a.get("title", "?")}
        _nm = _norm_name(pool[_vid])
        if _nm and _nm not in best:
            best[_nm] = pool[_vid]
    # affect match (characters MARY lane, selection side): candidate
    # tags in the chair's desired affect neighborhood score up. Capped —
    # taste weights still dispose.
    try:
        sys_path_push()
        from ensemble_cast import affect_for as _afffn
        _aff = _afffn(None, chair + " " + " ".join(chair_kw))
        _affwords = set(_aff.get("voice_words", []))
    except Exception:
        _affwords = set()
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
        # quality floor: junk auto-uploads (ALL-CAPS names, stutter-names
        # like "calm calm", <200 uses with no owner backing) never reach a
        # slate. Anchors + incumbent bypass (owner vouched).
        _nm = str(v.get("title") or v.get("name") or "")
        _uses = int(v.get("task_count") or 0)
        _anchored = any(str(_a.get("voice_id")) == vid for _a in anchors)
        _words = _nm.split()
        _wl = {w.lower() for w in _words}
        _junk = ((len(_nm) > 4 and _nm.upper() == _nm) or
                 (len(_words) > 1 and len(_wl) < len(_words)) or
                 (_nm.strip().lower() in {"calm", "sleep", "whisper", "narration",
                                          "story", "stories", "relax", "voice"} and len(_words) == 1) or
                 bool(_wl & {"null", "none", "test", "testing", "trial", "demo",
                             "sample", "temp", "xxx", "untitled"}) or
                 bool(__import__("re").search(r"['\"0-9_]", _nm)))
        if (_junk or _uses < 200) and vid != incumbent and not _anchored:
            continue
        tags = set((v.get("tags") or []))
        # token match (substring "male" in "female" was scoring cross-gender).
        # Each tag counts ONCE across all terms: theory claims first, then
        # affect, then overlap, then anchor. Same tags stacking four capped
        # terms is how 14-tag blanket voices (Fairy zzz) haunted every slate.
        _tag_toks = {t: set(str(t).lower().replace("-", " ").split())
                     for t in tags}
        _claimed: set = set()
        def _claim(pred):
            hits = {t for t, toks in _tag_toks.items() if pred(toks)}
            fresh = {t for t in hits
                     if not (_tag_toks[t] & _claimed)}
            _claimed.update(*[set(_tag_toks[t]) for t in hits])
            return sorted(fresh, key=lambda t: (-len(t), t))
        _thit = _claim(lambda toks: bool(toks & _arch_tags)) \
            if _arch_tags else []
        _amatch = sorted(
            {t for t in tags if t.lower() in _affwords
             and not (_tag_toks[t] & _claimed)},
            key=lambda t: (-len(t), t))
        _claimed.update(*[_tag_toks[t] for t in _amatch])
        overlap = sorted({t for t, toks in _tag_toks.items()
                          if any(k in toks for k in chair_kw)
                          and not (toks & _claimed)},
                         key=lambda t: (-len(t), t))
        _claimed.update(*[_tag_toks[t] for t in overlap])
        uses = int(v.get("task_count") or 0)
        likes = int(v.get("like_count") or 0)
        # score budget: theory 5 (prediction leads), taste overlap 4,
        # affect 2, anchor cross-taste 2, fame 1 + buzz 2 + lang 1.
        # Fame (total uses) is legacy, capped hard; buzz (like-rate) is
        # momentum — trending outranks famous.
        pop = min(1.0, math.log10(max(10, uses)) / 5.0) + \
            min(2.0, (likes / max(1, uses)) * 40.0)
        like_rate = likes / max(1, uses)
        langs = v.get("languages") or v.get("language") or []
        if isinstance(langs, str):
            langs = [langs]
        lang_ok = any(str(l).startswith("en") for l in langs)
        shared = vid in siblings
        # calibrated overlap: learned weight per tag, modulated around the
        # old +3 default (w=1 → 3.0, w=-1 → 0). Unknown tags → neutral.
        # Tag-stuffing guard: voices carrying 20+ tags would otherwise match
        # every query (observed: one voice topping all 21 packs). Overlap is
        # discounted by tag count — precision beats coverage.
        _tag_n = max(8, len(tags))
        overlap_score = round(min(4.0, sum(
            (1.5 + 1.5 * _taste_w(t, 0.5)) * 8.0 / _tag_n
            for t in overlap))
            + sum(_fww.get(t.lower(), 0.0) * 2.0
                  for t in tags), 1)
        if _amatch:
            overlap_score = round(overlap_score + min(2.0, len(_amatch)), 1)
        # _thit already computed above under claim priority (each tag once).
        if _thit:
            overlap_score = round(
                overlap_score + min(5.0, 1.5 * len(_thit)), 1)
        # precision: blanket tag coverage (14 tags matching everything)
        # is catalogue SEO, not fit. Tag-derived points scale down with
        # tag count — precision beats coverage.
        _prec = 8.0 / max(8, len(tags))
        score = round(overlap_score * _prec, 1)
        score = round(score + pop + (1 if lang_ok else -5)
                      - (8 if shared else 0), 1)
        reasons = []
        if _thit:
            reasons.append(f"theory fit ({_arch}: {', '.join(_thit[:4])})")
        if _amatch:
            reasons.append(f"affect match ({', '.join(_amatch[:3])})")
        if overlap:
            if len(overlap) == 1 and len(overlap[0]) <= 5:
                reasons.append(f"weak tag match ({overlap[0]}) — judge the sample")
            else:
                reasons.append(f"tags match vibe: {', '.join(overlap[:4])}")
        # anchor self-match excluded: a loved voice may not cite its OWN
        # tags as owner taste (Luna topping every slate off her own
        # vocabulary is the bug). Only OTHER anchors' tags count.
        # anchor is last in claim priority: already-counted tags don't
        # double-pay here either.
        anchor_hit = sorted({t for t in tags
                             if t.lower() in anchor_vocab
                             and anchor_src.get(t.lower()) != vid
                             and not (_tag_toks[t] & _claimed)},
                            key=lambda t: (-len(t), t))
        if not overlap and not anchor_hit:
            reasons.append("no tag overlap — sample decides")
        if anchor_hit:
            cited = sorted({anchor_vocab[t.lower()] for t in anchor_hit})
            reasons.append(f"owner taste ({', '.join(cited[:2])}): "
                           f"{', '.join(anchor_hit[:4])}")
            score = round(score + min(2.0, 1.0 * len(anchor_hit)), 1)
        # mismatch vetoes: vendor tags contradicting the graph's archetype
        # (dramatic tortoise, giggly crone). Each contradiction -3, cap -6.
        _vhit = sorted({t for t in tags
                        if set(str(t).lower().replace("-", " ").split())
                        & _vetoes},
                       key=lambda t: (-len(t), t)) if _vetoes else []
        if _vhit:
            score = round(score - min(6.0, 3.0 * len(_vhit)), 1)
            reasons.append(f"contradicts {(_cg or {}).get('archetype', '?')}: "
                           f"{', '.join(_vhit[:3])} — judge hard")
        if like_rate >= 0.02:
            reasons.append(f"trending ({like_rate:.1%} like-rate)")
        elif uses > 20000 and like_rate < 0.004:
            reasons.append("legacy fame, low love — judge the sample")
        else:
            reasons.append(f"{uses:,} prior uses"
                           + (" (proven)" if uses > 20000 else " (niche)"))
        if not lang_ok:
            reasons.append("WARNING: not English-first")
        if shared:
            reasons.append("WARNING: locked by a sibling channel")
        if vid == incumbent:
            reasons.append("current lock — re-pick to keep, or dethrone")
            score = round(score + 0.5, 1)  # tie-break for the devil known
        _anch_from = v.get("_anchor")
        if not _anch_from:
            for _aa in anchors:
                if str(_aa.get("voice_id")) == vid:
                    _anch_from = _aa.get("title", "?")
                    break
        if _anch_from:
            reasons.insert(0, f"your loved voice ({_anch_from})")
        # role fit: narrators carry (storytelling/narration + sleep-fit
        # counts double — the carrier metric); characters personify
        # (character-voice/delivery tags over generic narration).
        _toks_all = set().union(*_tag_toks.values()) if _tag_toks else set()
        if _is_narrator:
            if _toks_all & {"storytelling", "narration"}:
                score = round(score + 1.5, 1)
                reasons.append("carrier: storytelling/narration voice")
        else:
            if _toks_all & {"character-voice", "animated", "dramatic",
                            "character", "entertainment"}:
                score = round(score + 1.5, 1)
                reasons.append("persona: character voice, not carrier")
        _meas = (_ac or {}).get(vid, {})
        _sf = ((_meas.get("sleep_fit") or {}).get("score")
               if isinstance(_meas, dict) else None)
        _sf_mult = 2.0 if _is_narrator else 1.0
        if _sf is not None:
            if _sf >= 80:
                score = round(score + 1.5 * _sf_mult, 1)
                reasons.append(f"measured sleep-fit {_sf} (waveform, not tags)")
            elif _sf < 55:
                score = round(score - 1.5 * _sf_mult, 1)
                reasons.append(f"measured sleep-fit {_sf} — sample runs hot")
        scored.append({"voice_id": vid,
                       "name": v.get("title") or v.get("name"),
                       "language": langs[0] if langs else "?",
                       "tags": sorted(tags)[:8],
                       "sample": v.get("sample_audio"),
                       "uses": uses, "score": score,
                       "reason": "; ".join(reasons)})
    scored.sort(key=lambda c: c["score"], reverse=True)
    # listen before rank: measure top candidates' samples (cached per
    # voice), fit to the predicted band. Tag liars never reach the slate
    # on claims alone (Philosophy Deep: tagged deep/low, measures 500Hz).
    if _arch:
        try:
            sys_path_push()
            from character_engine import (fit_score as _fitscore,
                                          PACE_TARGET as _PT,
                                          DISP_WANT_LOW as _DWL)
            from ensemble_cast import ARCHETYPES as _ARCHT
            _band = {"pitch_hz": list(_ARCHT.get(_arch, {}).get(
                "pitch", (100, 160))),
                "rate_syl_s": _PT.get(_arch, 2.2),
                "dispersion": ("low" if _arch in _DWL else "high")}
            _mcpath = os.path.join(os.path.dirname(CHANNELS_DIR),
                                   "voice-measurements.json")
            try:
                _mc = json.load(open(_mcpath, encoding="utf-8"))
            except Exception:
                _mc = {}
            _dirty = False
            for _c in scored[:12]:
                _vid2, _samp = _c["voice_id"], _c.get("sample") or ""
                if not _samp or _vid2 in _mc:
                    continue
                try:
                    from voice_listen import listen as _listen
                    _mc[_vid2] = {"measured": _listen(_samp)}
                    _dirty = True
                except Exception:
                    continue
            if _dirty:
                try:
                    _tmp = _mcpath + ".tmp"
                    json.dump(_mc, open(_tmp, "w"), ensure_ascii=False)
                    os.replace(_tmp, _mcpath)
                except Exception:
                    pass
            for _c in scored:
                _m = (_mc.get(_c["voice_id"]) or {}).get("measured")
                if not _m:
                    continue
                _f = _fitscore(_m, _band)
                _c["score"] = round(_c["score"] + (_f["fit"] / 10.0) * 4.0, 1)
                _c["reason"] += (f"; heard: F0 {_m.get('f0_median_hz')}Hz, "
                                 f"{_m.get('syllables_per_sec')}/s, "
                                 f"fit {_f['fit']}/{_f['max']}")
                _f0v = _m.get("f0_median_hz") or 0
                if _f0v and _f0v > 2 * _band["pitch_hz"][1]:
                    _c["score"] = round(_c["score"] - 5.0, 1)
                    _c["reason"] += (" | TAG LIE: measures 2x above band — "
                                     "judge hard")
            scored.sort(key=lambda c: c["score"], reverse=True)
        except Exception:
            pass
    # slate assembly: incumbent always in (status-quo comparison), at most
    # 2 loved voices, remaining slots go to fresh voices by score. Loved
    # voices stay cited and one-click lockable — they just can't BE the
    # whole slate anymore (a tortoise served 5 anchors teaches nothing).
    _anchor_ids = {str(_a.get("voice_id") or "") for _a in anchors}
    _inc = [c for c in scored if c["voice_id"] == incumbent][:1] if incumbent else []
    _loved = [c for c in scored if c["voice_id"] in _anchor_ids
              and c["voice_id"] != incumbent][:2]
    _fresh = [c for c in scored if c["voice_id"] not in _anchor_ids
              and c["voice_id"] != incumbent]
    slate = _inc + _loved + _fresh
    # de-dupe (incumbent can also be loved), keep first occurrence
    _seen, _slate = set(), []
    for c in slate:
        if c["voice_id"] not in _seen:
            _seen.add(c["voice_id"])
            _slate.append(c)
    # non-English hard filter when the pool allows: a -5 penalty still
    # seated Spanish tigres on an English slate. Veto only if n English
    # candidates survive it.
    _en = [c for c in _slate
           if "WARNING: not English-first" not in c.get("reason", "")]
    if len(_en) >= n:
        _slate = _en
    _slate.sort(key=lambda c: c["score"], reverse=True)
    slate = _slate[:n]
    # BT verdict: fitted pairwise model over the top two (when calibrated).
    # Cited on the winner; same hot..cold shape as characters voice_battle.
    _bt, _verdict = None, None
    try:
        sys_path_push()
        from taste_profile import bt_predict as _btp
        _bt = _btp(_fn, (slate[0].get("tags", []) if len(slate) > 0 else []),
                   (slate[1].get("tags", []) if len(slate) > 1 else [])) \
            if len(slate) > 1 else None
    except Exception:
        _bt = None
    if _bt:
        slate[0]["bt_p"] = _bt["p"]
        slate[0]["reason"] += (f" | BT fit ({_fn}, acc {_bt['train_accuracy']}): "
                                f"P={_bt['p']} → {_bt['verdict']['state']}/"
                                f"{_bt['verdict']['action']}")
        _verdict = _bt["verdict"]
    else:
        _verdict = None
    # slate coherence: mean pairwise Jaccard over candidate tag sets.
    # 1.0 = five identical voices, 0.0 = five strangers. Reported, not
    # yet enforced — acoustic variance (F0/formants) replaces this once
    # the listening layer measures candidates.
    def _coherence(cands):
        tags = [set(str(t).lower() for t in (c.get("tags") or []))
                for c in cands]
        if len(tags) < 2:
            return 1.0
        sims = []
        for i in range(len(tags)):
            for j in range(i + 1, len(tags)):
                u = tags[i] | tags[j]
                sims.append(len(tags[i] & tags[j]) / len(u) if u else 0.0)
        return round(sum(sims) / len(sims), 3) if sims else 0.0
    liked = _liked_ids(channel_slug, chair)
    return {"ok": True, "channel": channel_slug, "chair": chair,
            "function": _fn,
            "archetype": {"name": _arch,
                          "pitch": _arch_prof.get("pitch"),
                          "delivery": (_arch_prof.get("delivery") or "")[:160]} if _arch else None,
            "character_profile": _character_profile(channel_slug, chair),
            "voice_profile": _vp,
            "function_calibrated": bool(_fww),
            "bt_verdict": _verdict,
            "queries": (_queries or vibe_queries(channel, chair)),
            "liked": sorted(liked),
            "candidates": slate,
            "coherence": _coherence(slate),
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
    prev = {"voice_id": c.get("fish_id", ""),
            "label": c.get("label", ""),
            "reason": c.get("lock_reason", "")}
    c["fish_id"] = voice_id
    c["status"] = "locked"
    c["lock_reason"] = reason
    c["locked_by"] = actor
    c["locked_at"] = int(time.time())
    c["previous"] = [p for p in (c.get("previous") or [])
                     if isinstance(p, dict)]
    if prev["voice_id"] and prev["voice_id"] != voice_id:
        c["previous"].append(prev)
    # dethroned history kept — re-lock restores in one click
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
    _samp = d.get("sample_audio") or (d.get("sample") or {}).get("audio", "")
    anchors.append({"voice_id": voice_id,
                    "title": d.get("title") or "",
                    "tags": d.get("tags") or [],
                    "languages": d.get("languages") or [],
                    "task_count": d.get("task_count") or 0,
                    "sample_audio": _samp,
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


def _character_profile(channel_slug: str, chair: str) -> dict | None:
    """Full character profile for assessment: dramatis match (mentions,
    dialogue, gender/age/role, sample lines, voice query) plus ensemble
    brief (pitch band, function, delivery). Returns None when the chair
    is a role (narrator) rather than a named character."""
    import glob as _gg
    ddir = os.path.join(CHANNELS_DIR, channel_slug, "dramatis")
    if not os.path.isdir(ddir):
        return None
    want = chair.strip().lower()
    best, best_n = None, 0
    for fp in sorted(_gg.glob(os.path.join(ddir, "*.json"))):
        try:
            d = json.load(open(fp, encoding="utf-8"))
        except Exception:
            continue
        for c in d.get("characters", []):
            nm = str(c.get("name", ""))
            if nm.lower() == want or want in nm.lower():
                n = int(c.get("dialogue_lines") or 0)
                if n >= best_n:
                    best_n = n
                    best = {"name": nm, "book": os.path.basename(fp)[:-5],
                            "mentions": c.get("mentions", 0),
                            "dialogue_lines": n,
                            "gender": c.get("gender"), "age": c.get("age"),
                            "role": c.get("role"),
                            "voice_query": c.get("voice_query", ""),
                            "sample_lines": (c.get("sample_line", "") or "")[:300],
                            "dialogue_how": c.get("dialogue_how", "")}
    if not best:
        return None
    try:
        sys_path_push()
        from ensemble_cast import brief_character, pitch_band
        prof = {"name": best["name"], "role": best["role"],
                "age": best["age"], "gender": best["gender"],
                "dialogue_lines": best["dialogue_lines"]}
        best["ensemble_brief"] = brief_character(prof)
        best["pitch_band_hz"] = pitch_band(best["role"], best["age"],
                                           best["gender"])
    except Exception:
        pass
    return best
