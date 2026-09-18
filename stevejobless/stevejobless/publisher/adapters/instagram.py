"""Instagram adapter — Graph API publishing."""
from __future__ import annotations

import time

import httpx

platform = "instagram"

GRAPH = "https://graph.facebook.com/v21.0"


def _wait_for_container(creation_id: str, token: str, timeout: int = 90) -> tuple[bool, str]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = httpx.get(f"{GRAPH}/{creation_id}",
                      params={"fields": "status_code", "access_token": token}, timeout=15)
        if r.status_code >= 400:
            return False, f"poll {r.status_code}: {r.text[:300]}"
        status = r.json().get("status_code")
        if status == "FINISHED":
            return True, ""
        if status == "ERROR":
            return False, f"container ERROR: {r.text[:300]}"
        time.sleep(3)
    return False, "container poll timeout"


def publish(content: str, media_urls: list[str] | None = None,
            settings: dict | None = None, account_extra: dict | None = None) -> tuple[bool, str, str]:
    extra = account_extra or {}
    ig_user_id = extra.get("ig_user_id", "")
    token = extra.get("access_token", "")

    if not (ig_user_id and token):
        return False, "", "IG_USER_ID / IG_TOKEN missing"

    settings = settings or {}
    media_url = (media_urls or [None])[0]
    caption = content[:2200]

    try:
        if media_url and media_url.endswith((".mp4", ".mov")):
            r = httpx.post(f"{GRAPH}/{ig_user_id}/media",
                           data={"media_type": "REELS", "video_url": media_url,
                                 "caption": caption, "access_token": token}, timeout=60)
        elif media_url:
            r = httpx.post(f"{GRAPH}/{ig_user_id}/media",
                           data={"image_url": media_url, "caption": caption,
                                 "access_token": token}, timeout=30)
        else:
            return False, "", "instagram requires media (image_url or video_url)"

        if r.status_code >= 400:
            return False, "", f"container: {r.status_code} {r.text[:300]}"
        creation_id = r.json()["id"]

        ok, err = _wait_for_container(creation_id, token)
        if not ok:
            return False, "", err

        r = httpx.post(f"{GRAPH}/{ig_user_id}/media_publish",
                       data={"creation_id": creation_id, "access_token": token}, timeout=30)
        if r.status_code >= 400:
            return False, "", f"publish: {r.status_code} {r.text[:300]}"
        return True, str(r.json().get("id", "")), ""
    except Exception as e:
        return False, "", f"instagram error: {e}"
