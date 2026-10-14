"""Taste profile compiler — distill owner taste into standing weights.

Inputs (all already recorded, no new infra):
  locks + reasons (channel records) ........... weight 3
  anchors + descriptors (voice-anchors.json) .. weight 2
  likes + notes (taste files) ................. weight 1
  dismissed ................................... weight -2
  verdicts (video picks) ...................... weight 2 (when present)

Output: studio/taste-profile.json:
  {weights: {feature: w}, rules: [...], anchors_cited: [...]}
Weights are smoothed preference rates per tag/descriptor word:
  w = (pos - neg) / (pos + neg + 2), clipped to [-1, 1].
Rules are owner verbatims matching never/no/not patterns + lock reasons.

propose() reads this file when present, else falls back to hand defaults.
Recompile after every lock/love/tick (cheap, pure).
"""
from __future__ import annotations

import json
import os
import re
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.normpath(os.path.join(_HERE, "..", "studio"))
CHANNELS = os.path.join(STUDIO, "channels")
PROFILE = os.path.join(STUDIO, "taste-profile.json")

_RULE_PAT = re.compile(
    r"\b(never|no|not|avoid|none of|keep out)\b.{0,60}", re.I)


def _load_json(path: str, default):
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
            return d if isinstance(d, (dict, list)) else default
    except Exception:
        return default


_LANE_STOP = {"and", "for", "the", "with", "from", "that", "this",
               "your", "our", "voice", "narrator", "chair"}


def compile_profile() -> dict:
    """Scan all taste artifacts → weights + rules. Pure, deterministic."""
    pos: dict[str, float] = {}
    neg: dict[str, float] = {}
    rules: list[str] = []
    seen_rules: set[str] = set()

    def _bump(words, w, negative=False):
        toks: list[str] = []
        for item in words:
            toks.extend(re.findall(r"[a-z]{3,}", str(item).lower()))
        for t in toks:
            if len(t) < 3:
                continue
            d = neg if negative else pos
            d[t] = d.get(t, 0.0) + w

    def _rule(text: str, src: str):
        for m in _RULE_PAT.finditer(text or ""):
            r = re.sub(r"\s+", " ", m.group(0)).strip()[:120]
            if r and r not in seen_rules:
                seen_rules.add(r)
                rules.append(f"{r} [{src}]")

    # anchors (weight 2) + their descriptors
    for a in _load_json(os.path.join(STUDIO, "voice-anchors.json"), []):
        if not isinstance(a, dict):
            continue
        _bump(a.get("tags") or [], 2.0)
        _bump(a.get("descriptors") or [], 2.0)
        _rule(a.get("note", ""), a.get("title", "anchor"))

    # channel locks (3), likes (1), dismissed (-2), notes (rules)
    if os.path.isdir(CHANNELS):
        for fn in sorted(os.listdir(CHANNELS)):
            if not fn.endswith(".json") or fn.endswith(
                    (".seed.json", "-taste.json")):
                continue
            rec = _load_json(os.path.join(CHANNELS, fn), {})
            if not isinstance(rec, dict):
                continue
            for c in (((rec.get("voice") or {}).get("chairs")) or {}).values():
                if not isinstance(c, dict) or not c.get("fish_id"):
                    continue
                _bump((c.get("label", "") or "").split(), 1.0)
                _bump([c.get("direction", "") or ""], 1.0)
                _rule(c.get("lock_reason", ""),
                      f"{rec.get('channel', fn)} lock")
                _bump([c.get("lock_reason", "") or ""], 3.0)
            # taste file: likes/notes/dismissed
            slug = rec.get("channel", fn[:-5])
            t = _load_json(os.path.join(CHANNELS, slug + "-taste.json"), {})
            for lk in t.get("likes") or []:
                if isinstance(lk, dict):
                    _bump([lk.get("name", "") or ""], 1.0)
                    _rule(lk.get("note", ""), "like")
            for fb in t.get("feedback") or []:
                if isinstance(fb, dict):
                    _rule(fb.get("text", ""), "feedback note")
            for vid in t.get("dismissed") or []:
                neg[f"voice:{vid}"] = neg.get(f"voice:{vid}", 0.0) + 2.0

    feats = set(pos) | set(neg)
    weights = {}
    for f in feats:
        p, n = pos.get(f, 0.0), neg.get(f, 0.0)
        w = (p - n) / (p + n + 2.0)
        if abs(w) >= 0.05:
            weights[f] = round(max(-1.0, min(1.0, w)), 3)

    # lane linkage: tags of voices locked on high-sleepy channels become
    # the sleep-lane rule (evidence, not assertion). Thumb likes/notes feed
    # visual rules the same way.
    lanes: dict = {}
    sleepy_tags: dict[str, float] = {}
    visual: list[str] = []
    if os.path.isdir(CHANNELS):
        for fn in sorted(os.listdir(CHANNELS)):
            if not fn.endswith(".json") or fn.endswith(
                    (".seed.json", "-taste.json")):
                continue
            rec = _load_json(os.path.join(CHANNELS, fn), {})
            if not isinstance(rec, dict):
                continue
            prof = rec.get("profile") or {}
            slug = rec.get("channel", fn[:-5])
            if float(prof.get("sleepy") or 0) >= 0.9:
                for c in (((rec.get("voice") or {}).get("chairs"))
                           or {}).values():
                    if isinstance(c, dict) and c.get("fish_id"):
                        for t in re.findall(
                                r"[a-z]{3,}",
                                ((c.get("label") or "") + " " +
                                 (c.get("direction") or "")).lower()):
                            if t not in _LANE_STOP:
                                sleepy_tags[t] = sleepy_tags.get(t, 0.0) + 1.0
            t = _load_json(os.path.join(CHANNELS, slug + "-taste.json"), {})
            for tl in t.get("thumb_likes") or []:
                if isinstance(tl, dict) and tl.get("note"):
                    visual.append(tl["note"][:120])
    if sleepy_tags:
        top = sorted(sleepy_tags.items(), key=lambda kv: -kv[1])[:10]
        lanes["sleepy"] = {"tags": [k for k, _ in top],
                           "rule": "sleepy>=0.9 channels lock: " +
                                   ", ".join(k for k, _ in top[:6])}
    if visual:
        lanes["visual"] = {"notes": visual[:10],
                           "rule": "owner thumb notes (latest first)"}

    profile = {"version": 2, "compiled_at": int(time.time()),
               "weights": dict(sorted(weights.items(),
                                      key=lambda kv: -abs(kv[1]))),
               "rules": rules[:40],
               "lanes": lanes,
               "n_features": len(weights)}
    with open(PROFILE, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=1, ensure_ascii=False)
    return profile


def load_profile() -> dict:
    return _load_json(PROFILE, {"weights": {}, "rules": []})


_CACHE: dict = {"mtime": 0, "profile": {}}


def _cached() -> dict:
    try:
        mt = os.path.getmtime(PROFILE)
    except OSError:
        return {"weights": {}, "rules": []}
    if mt != _CACHE["mtime"]:
        _CACHE["profile"] = load_profile()
        _CACHE["mtime"] = mt
    return _CACHE["profile"]


def weight_of(feature: str, default: float = 0.5) -> float:
    """Calibrated weight for one tag/word, or default when unknown."""
    w = _cached().get("weights", {}).get(str(feature).lower())
    return float(w) if w is not None else default


# ---- calibration studio: pairwise rankings → per-function weights ----
#
# Human ranks 5 options per function (narration/whisper/lecture/...);
# engine ranks too. Pairs (winner > loser) fit per-function weights:
# winner tags/descriptors +, loser -. Stored in profile["functions"].
# propose() blends global weights with the chair's function weights.

PAIRS_PATH = os.path.join(STUDIO, "taste-pairs.jsonl")

FUNCTIONS = ("narration", "whisper", "lecture", "character", "announcer")


def record_ranking(function: str, ordered_ids: list,
                   cards: list | None = None) -> dict:
    """Store a human ranking (best-first IDs) as pairs + refit function."""
    fn = str(function or "").strip().lower() or "general"
    ids = [str(x) for x in (ordered_ids or []) if str(x).strip()][:8]
    if len(ids) < 2:
        return {"ok": False, "reason": "need 2+ ranked ids"}
    by_id = {}
    if cards:
        for c in cards:
            vid = str((c.get("voice_id") or ""))
            if vid:
                by_id[vid] = c
    pairs = []
    for i, w in enumerate(ids):
        for l in ids[i + 1:]:
            pairs.append({"function": fn, "winner": w, "loser": l,
                          "ts": int(time.time()),
                          "w_tags": (by_id.get(w) or {}).get("tags", []),
                          "l_tags": (by_id.get(l) or {}).get("tags", [])})
    with open(PAIRS_PATH, "a", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(p) + "\n")
    return {"ok": True, "function": fn, "pairs": len(pairs),
            "fit": fit_function(fn)}


def _pairs_for(fn: str) -> list:
    out = []
    try:
        with open(PAIRS_PATH, encoding="utf-8") as f:
            for line in f:
                try:
                    p = json.loads(line)
                except Exception:
                    continue
                if isinstance(p, dict) and p.get("function") == fn:
                    out.append(p)
    except OSError:
        pass
    return out


def fit_function(fn: str) -> dict:
    """Fit per-function weights from pairs; persist into profile."""
    pairs = _pairs_for(fn)
    pos: dict[str, float] = {}
    neg: dict[str, float] = {}
    for p in pairs:
        for t in p.get("w_tags") or []:
            t = str(t).strip().lower()
            if len(t) >= 3:
                pos[t] = pos.get(t, 0.0) + 1.0
        for t in p.get("l_tags") or []:
            t = str(t).strip().lower()
            if len(t) >= 3:
                neg[t] = neg.get(t, 0.0) + 1.0
    weights = {}
    for f in set(pos) | set(neg):
        w = (pos.get(f, 0.0) - neg.get(f, 0.0)) / (
            pos.get(f, 0.0) + neg.get(f, 0.0) + 2.0)
        if abs(w) >= 0.05:
            weights[f] = round(max(-1.0, min(1.0, w)), 3)
    prof = load_profile()
    funcs = prof.get("functions") or {}
    funcs[fn] = {"weights": dict(sorted(
        weights.items(), key=lambda kv: -abs(kv[1]))),
        "pairs": len(pairs), "fitted_at": int(time.time())}
    prof["functions"] = funcs
    with open(PROFILE, "w", encoding="utf-8") as f:
        json.dump(prof, f, indent=1, ensure_ascii=False)
    _CACHE["mtime"] = 0  # bust weight cache
    return {"function": fn, "pairs": len(pairs),
            "weights": funcs[fn]["weights"]}


def function_weights(fn: str) -> dict:
    """Fitted weights for a function, {} when uncalibrated."""
    return (_cached().get("functions") or {}).get(fn, {}).get("weights", {})


def chair_function(chair: str, direction: str = "") -> str:
    """Map a chair to a calibration function by keywords."""
    s = f"{chair} {direction}".lower()
    if any(k in s for k in ("whisper", "yuki", "ghost", "veiled")):
        return "whisper"
    if any(k in s for k in ("lectur", "teacher", "professor", "explain")):
        return "lecture"
    if any(k in s for k in ("character", "goblin", "witch", "giant",
                            "mouse", "kid", "boy", "girl")):
        return "character"
    if any(k in s for k in ("announc", "anchor", "news", "host")):
        return "announcer"
    return "narration"
