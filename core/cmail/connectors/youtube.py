from __future__ import annotations

import httpx

from .base import Observation
from ..config import settings

OEMBED = "https://www.youtube.com/oembed"


class YouTubeConnector:
    """Video existence via oEmbed (no key): a video_id that resolves is
    READY with title/author observed. Analytics (views, retention, CTR)
    needs OAuth — without it, a HUMAN task to connect read-only API scope.
    Publishing always stays behind the human decide gate; this connector
    only observes."""

    kind = "youtube"

    def observe(self, desired: dict) -> Observation:
        video_id = (desired.get("video_id") or "").strip()
        want_stats = bool(desired.get("want_stats"))
        if not video_id:
            return Observation("MISSING", "No video to check", executor="HUMAN",
                               human_title="Queue a video",
                               human_instructions="Publish a set (gated), record the video id back here for readback.",
                               estimate_seconds=120, priority=50)
        try:
            with httpx.Client(timeout=settings.http_timeout) as client:
                r = client.get(OEMBED, params={"url": f"https://www.youtube.com/watch?v={video_id}",
                                               "format": "json"})
            if r.status_code == 404:
                return Observation("MISSING", f"Video {video_id} not found (private/removed?)",
                                   observed={"video_id": video_id}, executor="HUMAN",
                                   human_title="Check video visibility",
                                   human_instructions=f"Video {video_id} does not resolve publicly. Confirm it is public and the id is exact.",
                                   estimate_seconds=120, priority=60)
            if r.status_code != 200:
                return Observation("UNKNOWN", f"YouTube lookup unavailable (HTTP {r.status_code})",
                                   observed={"video_id": video_id})
            body = r.json()
            observed = {"video_id": video_id, "title": body.get("title", ""),
                        "author": body.get("author_name", "")}
            if want_stats:
                observed["stats"] = "UNKNOWN (needs OAuth read-only scope)"
                return Observation("MISSING", f"{body.get('title', video_id)} live; stats need API scope",
                                   observed=observed, executor="HUMAN",
                                   human_title="Connect YouTube Analytics (read-only)",
                                   human_instructions="OAuth with youtube.readonly + yt-analytics.readonly scopes (see Postiz youtube guide). Analytics is evidence, never authority.",
                                   estimate_seconds=600, priority=55)
            return Observation("READY", f"Video live: {body.get('title', video_id)}",
                               observed=observed)
        except Exception as exc:
            return Observation("UNKNOWN", f"YouTube check failed: {exc}",
                               observed={"video_id": video_id})
