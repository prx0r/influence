"""LinkedIn adapter — UGC Post API."""
from __future__ import annotations

import httpx

platform = "linkedin"

UGC = "https://api.linkedin.com/v2/ugcPosts"


def publish(content: str, media_urls: list[str] | None = None,
            settings: dict | None = None, account_extra: dict | None = None) -> tuple[bool, str, str]:
    extra = account_extra or {}
    token = extra.get("access_token", "")
    author_urn = extra.get("author_urn", "")

    if not (token and author_urn):
        return False, "", "LINKEDIN_ACCESS_TOKEN / AUTHOR_URN missing"

    payload: dict = {
        "author": author_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": content[:3000]},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }

    asset_urn = (settings or {}).get("asset_urn")
    if asset_urn:
        payload["specificContent"]["com.linkedin.ugc.ShareContent"].update({
            "shareMediaCategory": "IMAGE",
            "media": [{"status": "READY", "media": asset_urn}],
        })

    try:
        r = httpx.post(UGC, headers={
            "Authorization": f"Bearer {token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        }, json=payload, timeout=30)
        if r.status_code >= 400:
            return False, "", f"linkedin: {r.status_code} {r.text[:400]}"
        urn = r.headers.get("x-restli-id") or r.json().get("id", "")
        return True, str(urn), ""
    except Exception as e:
        return False, "", f"linkedin error: {e}"
