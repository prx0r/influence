"""Facebook Pages adapter — Graph API."""
from __future__ import annotations

import httpx

platform = "facebook"

GRAPH = "https://graph.facebook.com/v21.0"


def publish(content: str, media_urls: list[str] | None = None,
            settings: dict | None = None, account_extra: dict | None = None) -> tuple[bool, str, str]:
    extra = account_extra or {}
    page_id = extra.get("page_id", "")
    token = extra.get("access_token", "")

    if not (page_id and token):
        return False, "", "FACEBOOK_PAGE_ID / PAGE_TOKEN missing"

    media_url = (media_urls or [None])[0]

    try:
        if media_url:
            r = httpx.post(f"{GRAPH}/{page_id}/feed", data={
                "message": content[:63206], "link": media_url, "access_token": token,
            }, timeout=30)
        else:
            r = httpx.post(f"{GRAPH}/{page_id}/feed", data={
                "message": content[:63206], "access_token": token,
            }, timeout=30)

        if r.status_code >= 400:
            return False, "", f"facebook: {r.status_code} {r.text[:300]}"
        post_id = r.json().get("id", "")
        return True, str(post_id), ""
    except Exception as e:
        return False, "", f"facebook error: {e}"
