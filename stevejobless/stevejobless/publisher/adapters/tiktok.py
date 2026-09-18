"""TikTok adapter — Content Posting API v2."""
from __future__ import annotations

import time

import httpx

platform = "tiktok"

BASE = "https://open.tiktokapis.com/v2"


def publish(content: str, media_urls: list[str] | None = None,
            settings: dict | None = None, account_extra: dict | None = None) -> tuple[bool, str, str]:
    extra = account_extra or {}
    token = extra.get("access_token", "")
    if not token:
        return False, "", "TIKTOK_ACCESS_TOKEN missing"

    video_url = (media_urls or [None])[0]
    if not video_url:
        return False, "", "tiktok requires video_url in media_urls"

    settings = settings or {}
    caption = content[:2200]
    privacy = settings.get("privacy_level", "PUBLIC_TO_EVERYONE")

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8"}

    try:
        init_r = httpx.post(f"{BASE}/post/publish/video/init/", headers=headers, json={
            "post_info": {
                "title": caption, "privacy_level": privacy,
                "disable_duet": False, "disable_comment": False,
                "disable_stitch": False, "video_cover_timestamp_ms": 1000,
            },
            "source_info": {"source": "PULL_FROM_URL", "video_url": video_url},
        }, timeout=30)
        init_r.raise_for_status()
        init_data = init_r.json()

        if init_data.get("error", {}).get("code", "ok") != "ok":
            return False, "", f"TikTok init error: {init_data['error'].get('message', 'unknown')}"

        publish_id = init_data.get("data", {}).get("publish_id", "")
        if not publish_id:
            return False, "", "TikTok returned no publish_id"

        for _ in range(12):
            time.sleep(5)
            status_r = httpx.post(f"{BASE}/post/publish/status/fetch/",
                                  headers=headers, json={"publish_id": publish_id}, timeout=15)
            status_r.raise_for_status()
            status = status_r.json().get("data", {}).get("status", "")
            if status == "PUBLISH_COMPLETE":
                post_id = str(status_r.json().get("data", {}).get("publicaly_available_post_id", [publish_id])[0])
                return True, post_id, ""
            if status in ("FAILED", "PUBLISH_FAILED"):
                reason = status_r.json().get("data", {}).get("fail_reason", "unknown")
                return False, "", f"TikTok publish failed: {reason}"

        return True, publish_id, ""
    except httpx.HTTPStatusError as e:
        return False, "", f"HTTP {e.response.status_code}: {e.response.text[:300]}"
    except Exception as e:
        return False, "", f"tiktok error: {e}"
