"""Adapter base — retry, content rules, analytics."""
from __future__ import annotations

import time
from typing import Any


MAX_CONTENT_LENGTH = {
    "x": 280,
    "twitter": 280,
    "instagram": 2200,
    "facebook": 63206,
    "linkedin": 3000,
    "tiktok": 2200,
    "youtube": 5000,
    "bluesky": 300,
    "threads": 500,
    "telegram": 4096,
    "pinterest": 500,
    "mastodon": 500,
}


def sanitize_content(content: str, platform: str) -> str:
    """Trim + clean content for platform limits."""
    limit = MAX_CONTENT_LENGTH.get(platform, 5000)
    if len(content) > limit:
        content = content[:limit - 3] + "..."
    return content.strip()


def retry_publish(fn, *args, max_retries: int = 3, delay: float = 2.0, **kwargs) -> tuple[bool, str, str]:
    """Retry adapter.publish() with exponential backoff."""
    last_err = ""
    for attempt in range(max_retries):
        try:
            ok, post_id, err = fn(*args, **kwargs)
            if ok:
                return True, post_id, ""
            last_err = err
            if "rate_limit" in err.lower() or "429" in err:
                time.sleep(delay * (2 ** attempt))
                continue
            return False, "", err
        except Exception as e:
            last_err = str(e)
            time.sleep(delay * (2 ** attempt))
    return False, "", f"failed after {max_retries} attempts: {last_err}"


def parse_analytics(platform: str, raw: dict) -> dict:
    """Normalize platform analytics to common schema."""
    common = {
        "platform": platform,
        "impressions": raw.get("impressions", 0),
        "reach": raw.get("reach", 0),
        "engagement": raw.get("engagement", 0),
        "likes": raw.get("like_count", raw.get("likes", 0)),
        "comments": raw.get("comment_count", raw.get("comments", 0)),
        "shares": raw.get("share_count", raw.get("retweet_count", raw.get("shares", 0))),
        "saves": raw.get("bookmark_count", raw.get("saves", 0)),
    }
    total = max(common["impressions"], 1)
    common["engagement_rate"] = round(common["engagement"] / total * 100, 2)
    return common
