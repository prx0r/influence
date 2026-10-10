"""Analytics pull — metrics back into the ledger → re-rank.

YouTube first (key in vault). X/IG/TikTok stubs follow the same shape.
Every pull writes to channel_state.record_metrics + an action row.

Feedback loop: metrics → ledger → re-rank next batch (sleepintel pattern).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, os.path.dirname(_HERE))

try:
    from pipeline.channel_state import record_metrics
    from pipeline.actions import log_action
except ImportError:
    from channel_state import record_metrics
    from actions import log_action


def _vault(key: str) -> str:
    try:
        return subprocess.run(
            ["agent-vault", "vault", "credential", "get", key, "--vault", "oracle"],
            capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        return ""


def _get(url: str) -> dict:
    with urllib.request.urlopen(urllib.request.Request(url), timeout=20) as r:
        return json.loads(r.read())


def youtube_channel(handle: str, brand_slug: str = "oddhobb") -> dict:
    """Pull channel stats + recent videos. Returns summary, logs action."""
    key = _vault("YOUTUBE_API_KEY")
    if not key:
        return {"ok": False, "reason": "no YOUTUBE_API_KEY"}
    try:
        d = _get(f"https://www.googleapis.com/youtube/v3/channels"
                 f"?part=snippet,statistics,contentDetails&forHandle={handle.lstrip('@')}&key={key}")
        items = d.get("items", [])
        if not items:
            log_action("youtube", f"channel lookup {handle} (not found)", 0.0,
                       campaign="analytics", project_slug=brand_slug,
                       gates_passed=0, gates_total=1, status="FAIL")
            return {"ok": False, "reason": f"no channel for {handle} (unclaimed?)"}
        c = items[0]
        st = c.get("statistics", {})
        subs = int(st.get("subscriberCount", 0))
        views = int(st.get("viewCount", 0))
        record_metrics("youtube", handle, views=views, db_path=os.getenv("DASH_DB", ""))
        log_action("youtube", f"channel stats {handle}", 0.0,
                   campaign="analytics", project_slug=brand_slug,
                   external_id=c["id"], gates_passed=1, gates_total=1, status="PASS")
        return {"ok": True, "channel_id": c["id"],
                "title": c["snippet"]["title"],
                "subs": subs, "views": views,
                "videos": st.get("videoCount")}
    except Exception as e:
        return {"ok": False, "reason": str(e)[:200]}


def youtube_recent_videos(channel_id: str, max_results: int = 10) -> dict:
    """Recent uploads with per-video stats."""
    key = _vault("YOUTUBE_API_KEY")
    if not key:
        return {"ok": False, "reason": "no key"}
    try:
        # uploads playlist
        ch = _get(f"https://www.googleapis.com/youtube/v3/channels"
                  f"?part=contentDetails&id={channel_id}&key={key}")
        uploads = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        pl = _get(f"https://www.googleapis.com/youtube/v3/playlistItems"
                  f"?part=snippet,contentDetails&playlistId={uploads}"
                  f"&maxResults={max_results}&key={key}")
        vids = [it["contentDetails"]["videoId"] for it in pl.get("items", [])]
        if not vids:
            return {"ok": True, "videos": []}
        vs = _get(f"https://www.googleapis.com/youtube/v3/videos"
                  f"?part=snippet,statistics&id={','.join(vids)}&key={key}")
        return {"ok": True, "videos": [{
            "id": v["id"], "title": v["snippet"]["title"][:80],
            "published": v["snippet"]["publishedAt"][:10],
            "views": int(v["statistics"].get("viewCount", 0)),
            "likes": int(v["statistics"].get("likeCount", 0)),
            "comments": int(v["statistics"].get("commentCount", 0)),
        } for v in vs.get("items", [])]}
    except Exception as e:
        return {"ok": False, "reason": str(e)[:200]}


# Stubs — same shape, wire when tokens land
def x_metrics(handle: str) -> dict:
    return {"ok": False, "reason": "X API keys not in vault (need OAuth1 set)"}


def instagram_metrics(handle: str) -> dict:
    return {"ok": False, "reason": "IG Graph token not in vault"}


def tiktok_metrics(handle: str) -> dict:
    return {"ok": False, "reason": "TikTok Content Posting app not approved"}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", default="@oddhobbstudio")
    ap.add_argument("--videos", default=None, help="channel_id for recent videos")
    ap.add_argument("--brand", default="oddhobb")
    args = ap.parse_args()
    if args.videos:
        print(json.dumps(youtube_recent_videos(args.videos), indent=1)[:2000])
    else:
        print(json.dumps(youtube_channel(args.channel, args.brand), indent=1))
