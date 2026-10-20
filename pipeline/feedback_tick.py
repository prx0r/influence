"""Feedback tick (L3): published videoIds -> stats -> verdict rows.

Data-API-honest gates only (views/likes/comments). AVD/CTR/retention need
the Analytics API + OAuth — recorded as pending gates, NEVER faked.
Verdicts write to channel_state.record_metrics + the actions ledger;
L1 reads the re-ranked queue from there. Numbers kill, not vibes.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
try:
    from pipeline import analytics as _an
    from pipeline.channel_state import record_metrics
    from pipeline.actions import log_action
except ImportError:
    import analytics as _an
    from channel_state import record_metrics
    from actions import log_action

# Data-API-evaluable gates (sleep-channel scale; tune from ledger history)
GATES = {
    "velocity_floor_views_per_day": 5.0,
    "engagement_floor": 0.005,  # (likes+comments)/views
    "min_views_for_verdict": 50,  # below this: collecting, not killed
}


def _age_days(published: str) -> float:
    try:
        dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
        return max((datetime.now(timezone.utc) - dt).total_seconds() / 86400, 0.25)
    except Exception:
        return 1.0


def evaluate(video: dict, gates: dict | None = None) -> dict:
    """Pure function: stats dict -> verdict. Unit-testable, no network."""
    g = gates or GATES
    v = {"videoId": video.get("id"), "title": video.get("title", "")[:80]}
    views = int(video.get("views", 0) or 0)
    likes = int(video.get("likes", 0) or 0)
    comments = int(video.get("comments", 0) or 0)
    if views < g["min_views_for_verdict"]:
        return {**v, "views": views, "verdict": "collecting",
                "action": "hold — not enough data, re-check next tick"}
    vel = views / _age_days(video.get("published", ""))
    eng = (likes + comments) / max(views, 1)
    fails = []
    if vel < g["velocity_floor_views_per_day"]:
        fails.append(f"velocity {vel:.1f}/day < {g['velocity_floor_views_per_day']}")
    if eng < g["engagement_floor"]:
        fails.append(f"engagement {eng:.3%} < {g['engagement_floor']:.1%}")
    verdict = "kill" if fails else "continue"
    action = ("cut from rotation, reason logged; slot goes to next queue item"
              if fails else
              "winner — etch chain + series order; twin the format")
    return {**v, "views": views, "likes": likes, "comments": comments,
            "velocity_per_day": round(vel, 1), "engagement": round(eng, 4),
            "verdict": verdict, "reasons": fails, "action": action,
            "pending_gates": ["AVD>40%", "CTR floor", "night-two retention "
                              "(need Analytics API OAuth — not evaluated)"]}


def tick(video_ids: list[str], brand_slug: str = "oddhobb",
         gates: dict | None = None) -> dict:
    """Pull stats (vault key, read-only) -> verdicts -> ledger rows."""
    key_probe = _an.youtube_recent_videos.__globals__.get("_vault", lambda *a: "")("YOUTUBE_API_KEY")
    if not key_probe:
        return {"ok": False, "reason": "no YOUTUBE_API_KEY in vault"}
    import urllib.request as _u
    try:
        d = json.loads(_u.urlopen(_u.Request(
            "https://www.googleapis.com/youtube/v3/videos"
            f"?part=snippet,statistics&id={','.join(video_ids)}"
            f"&key={key_probe}"), timeout=20).read())
    except Exception as e:
        return {"ok": False, "reason": str(e)[:200]}
    verdicts = []
    for it in d.get("items", []):
        v = {"id": it["id"], "title": it["snippet"]["title"][:80],
             "published": it["snippet"]["publishedAt"][:10],
             "views": int(it["statistics"].get("viewCount", 0)),
             "likes": int(it["statistics"].get("likeCount", 0)),
             "comments": int(it["statistics"].get("commentCount", 0))}
        vd = evaluate(v, gates)
        verdicts.append(vd)
        try:
            record_metrics("youtube", it["id"], views=v["views"],
                           db_path=os.getenv("DASH_DB", ""))
            log_action("youtube", f"verdict {vd['verdict']}: {v['title']}",
                       0.0, campaign="feedback", project_slug=brand_slug,
                       external_id=it["id"],
                       gates_passed=0 if vd["verdict"] == "kill" else 1,
                       gates_total=1,
                       status="KILL" if vd["verdict"] == "kill" else "PASS")
        except Exception:
            pass
    return {"ok": True, "verdicts": verdicts}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--videos", default="", help="comma-separated videoIds")
    ap.add_argument("--channel", default=None, help="channel_id for uploads pull")
    ap.add_argument("--brand", default="oddhobb")
    a = ap.parse_args()
    if a.channel:
        print(json.dumps(_an.youtube_recent_videos(a.channel), indent=1)[:3000])
    elif a.videos:
        print(json.dumps(tick(a.videos.split(","), a.brand), indent=1)[:4000])
    else:
        print(json.dumps(evaluate({"id": "demo", "title": "demo",
                                   "published": "2026-10-01",
                                   "views": 120, "likes": 2,
                                   "comments": 0}), indent=1))
