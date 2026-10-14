"""Jev scoring for channels — ported from influence2 (same owner).

Sources: pipeline/content_score.py (X-algorithm remap, Apache-2.0 lineage),
pipeline/feedback.py (SOURCE_WEIGHTS + fuse), pipeline/momentum.py
(Wilder RSI). Reimplemented here channel-first (no arena dependency):
youtube.stats leads; arena/battle sources stay defined for later.

All pure stdlib. No network. No model calls. $0.
"""
from __future__ import annotations

import math

# --- engagement scorer (content_score.py) ---

WEIGHTS = {
    "like": 30.0,
    "comment": 13.5,
    "comment_with_creator_reply": 75.0,
    "share": 20.0,
    "subscribe": 50.0,
    "high_retention_view": 15.0,
    "dwell_second": 0.5,
    "dislike": -15.0,
    "low_retention_penalty": -25.0,
}

HALF_LIFE_DAYS = 7.0
DIVERSITY_DECAY = 0.85
DIVERSITY_WINDOW = 5


def engagement_score(video: dict, weights: dict | None = None) -> dict:
    """Score one video from metrics. See influence2 for field contract."""
    w = weights or WEIGHTS
    views = max(1, int(video.get("views") or 0))
    likes = int(video.get("likes") or 0)
    comments = int(video.get("comments") or 0)
    shares = int(video.get("shares") or 0)
    subs = int(video.get("subs_gained") or 0)
    avd = float(video.get("avg_view_duration") or 0)
    dur = max(1, float(video.get("duration") or 60))
    dislikes = int(video.get("dislikes") or 0)
    creator_replied = bool(video.get("creator_replied"))
    retention = min(1.0, avd / dur)
    parts = {}
    parts["likes"] = likes / views * 100 * w["like"] / 30.0
    comment_base = comments / views * 100 * w["comment"] / 13.5
    if creator_replied and comments > 0:
        comment_base += w["comment_with_creator_reply"] / 10.0
    parts["comments"] = comment_base
    parts["shares"] = shares / views * 100 * w["share"] / 20.0
    parts["subs"] = subs / views * 100 * w["subscribe"] / 50.0
    if retention >= 0.5:
        parts["retention"] = w["high_retention_view"] / 10.0
    elif retention < 0.2 and views > 100:
        parts["retention"] = w["low_retention_penalty"] / 10.0
    else:
        parts["retention"] = (retention - 0.2) * 10.0
    parts["dwell"] = min(10.0, avd * w["dwell_second"] / 10.0)
    parts["dislikes"] = -(dislikes / views) * 100 * abs(w["dislike"]) / 15.0
    raw = sum(parts.values())
    age = float(video.get("age_days") or 0)
    decay = 0.5 ** (age / HALF_LIFE_DAYS) if age > 0 else 1.0
    parts["recency_decay"] = decay
    return {"score": round(raw * decay, 2),
            "parts": {k: round(v, 2) for k, v in parts.items()},
            "retention": round(retention, 3)}


def rank_videos(videos: list[dict], weights: dict | None = None) -> list[dict]:
    """Score + rank with format-diversity penalty (no same-format runs)."""
    scored = [{**v, **engagement_score(v, weights)} for v in videos]
    scored.sort(key=lambda x: x["score"], reverse=True)
    seen: dict[str, int] = {}
    for v in scored:
        fmt = str(v.get("format") or v.get("category") or "unknown")
        n = seen.get(fmt, 0)
        if n > 0:
            v["diversity_penalty"] = round(DIVERSITY_DECAY ** n, 3)
            v["score"] = round(v["score"] * v["diversity_penalty"], 2)
        seen[fmt] = n + 1
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


def channel_health(videos: list[dict]) -> dict:
    """Aggregate channel verdict from scored videos."""
    if not videos:
        return {"videos": 0, "avg_score": 0, "top_format": None,
                "verdict": "no_data"}
    scored = rank_videos(videos)
    scores = [s["score"] for s in scored]
    avg = sum(scores) / len(scores)
    by_fmt: dict[str, list[float]] = {}
    for s in scored:
        by_fmt.setdefault(str(s.get("format") or "unknown"), []).append(s["score"])
    top_fmt = max(by_fmt.items(), key=lambda kv: sum(kv[1]) / len(kv[1]))[0]
    verdict = ("strong" if avg >= 10 else "healthy" if avg >= 5
               else "weak" if avg >= 1 else "critical")
    return {"videos": len(videos), "avg_score": round(avg, 2),
            "top_format": top_fmt, "verdict": verdict,
            "ranked": [{"title": s.get("title"), "score": s["score"]}
                       for s in scored[:5]]}


# --- fusion (feedback.py, channel-first) ---
# Audience wallet-votes (subs) outrank passive signals (views). Weights
# renormalize over active sources per content item.

SOURCE_WEIGHTS = {
    "youtube.stats": 0.35,     # views/likes/comments/subs (our main truth)
    "watch.retention": 0.25,   # completion — attention revealed
    "feedbacks": 0.12,         # human 0-3 ratings + comments read
    "youtube.deep": 0.08,      # transcript/quality signals
    "arena.votes": 0.10,       # defined for later (characters lane)
    "battle.scores": 0.05,     # model scores (not audience)
    "pogs": 0.05,              # defined for later
}

_VERDICTS = [(70, "hot"), (55, "growing"), (40, "steady"), (25, "cooling")]


def fuse(signals: list[dict]) -> dict:
    """Combine signals per content_id. Signal: {source, content_id,
    score_0_100, metrics?}. Returns {content_id: {score, verdict, signals}}."""
    by_content: dict[str, list[dict]] = {}
    for s in signals:
        w = SOURCE_WEIGHTS.get(s.get("source", ""), 0.0)
        if w > 0:
            by_content.setdefault(s["content_id"], []).append({**s, "w": w})
    out = {}
    for cid, sigs in by_content.items():
        total = sum(s["w"] for s in sigs)
        if total <= 0:
            continue
        score = sum(s["score_0_100"] * s["w"] for s in sigs) / total
        verdict = next((v for t, v in _VERDICTS if score >= t), "cold")
        out[cid] = {"score": round(score, 1), "verdict": verdict,
                    "signals": {s["source"]: {"score": s["score_0_100"],
                                              "weight": s["w"]} for s in sigs}}
    return out


# --- momentum (momentum.py: Wilder RSI + channel signal) ---

def rsi(series: list[float], period: int = 14) -> list[float | None]:
    if len(series) < period + 1:
        return [None] * len(series)
    gains, losses = [], []
    for i in range(1, len(series)):
        d = series[i] - series[i - 1]
        gains.append(max(0.0, d))
        losses.append(max(0.0, -d))
    ag = sum(gains[:period]) / period
    al = sum(losses[:period]) / period
    out: list[float | None] = [None] * period
    out.append(100.0 if al == 0 else 100 - 100 / (1 + ag / al))
    for i in range(period + 1, len(series)):
        d = series[i] - series[i - 1]
        ag = (ag * (period - 1) + max(0.0, d)) / period
        al = (al * (period - 1) + max(0.0, -d)) / period
        out.append(100.0 if al == 0 else 100 - 100 / (1 + ag / al))
    return out


def channel_momentum(daily_views: list[float]) -> dict:
    """Trend read: rising/hot/cooling/dead from view velocity + RSI."""
    if len(daily_views) < 15:
        return {"signal": "too_little_data", "rsi": None}
    r = [x for x in rsi(daily_views) if x is not None]
    last = r[-1] if r else 50.0
    vel = (daily_views[-1] - daily_views[-7]) / max(1.0, daily_views[-7])
    if last >= 70 and vel > 0.1:
        sig = "surging"
    elif last >= 55:
        sig = "rising"
    elif last <= 30 and vel < -0.1:
        sig = "fading"
    elif last <= 45:
        sig = "cooling"
    else:
        sig = "steady"
    return {"signal": sig, "rsi": round(last, 1),
            "velocity_7d": round(vel, 3)}
