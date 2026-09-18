"""YouTube adapter — Data API v3 resumable upload."""
from __future__ import annotations

import json
import mimetypes
from pathlib import Path

import httpx

platform = "youtube"

OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"


def _refresh_access_token(client: httpx.Client, client_id: str, client_secret: str,
                          refresh_token: str) -> tuple[str | None, str]:
    try:
        r = client.post(OAUTH_TOKEN_URL, data={
            "client_id": client_id, "client_secret": client_secret,
            "refresh_token": refresh_token, "grant_type": "refresh_token",
        }, timeout=30)
    except httpx.HTTPError as e:
        return None, f"token refresh error: {e}"
    if r.status_code >= 400:
        return None, f"token refresh HTTP {r.status_code}: {r.text[:200]}"
    return r.json().get("access_token"), ""


def publish(content: str, media_urls: list[str] | None = None,
            settings: dict | None = None, account_extra: dict | None = None) -> tuple[bool, str, str]:
    extra = account_extra or {}
    client_id = extra.get("client_id", "")
    client_secret = extra.get("client_secret", "")
    refresh_token = extra.get("refresh_token", "")

    if not all([client_id, client_secret, refresh_token]):
        return False, "", "YOUTUBE_CLIENT_ID / CLIENT_SECRET / REFRESH_TOKEN missing"

    video_path = (media_urls or [None])[0]
    if not video_path:
        return False, "", "youtube requires video_path in media_urls"

    p = Path(video_path)
    if not p.exists():
        return False, "", f"video not found: {video_path}"

    settings = settings or {}
    title = settings.get("title", content[:100])[:100]
    description = settings.get("description", content)[:5000]
    tags = settings.get("tags", [])
    privacy = settings.get("privacy", "public")

    if "#shorts" not in (title.lower() + " " + description.lower()):
        description += "\n\n#Shorts"

    metadata = {
        "snippet": {"title": title, "description": description, "categoryId": settings.get("category_id", "22"),
                     "tags": [str(t) for t in tags][:30]},
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
    }
    mime_type = mimetypes.guess_type(str(p))[0] or "video/mp4"

    with httpx.Client() as client:
        access_token, err = _refresh_access_token(client, client_id, client_secret, refresh_token)
        if not access_token:
            return False, "", err

        try:
            r = client.post(UPLOAD_URL, params={"uploadType": "resumable", "part": "snippet,status"},
                            headers={"Authorization": f"Bearer {access_token}",
                                     "Content-Type": "application/json; charset=UTF-8",
                                     "X-Upload-Content-Type": mime_type,
                                     "X-Upload-Content-Length": str(p.stat().st_size)},
                            content=json.dumps(metadata), timeout=30)
        except httpx.HTTPError as e:
            return False, "", f"init upload error: {e}"
        if r.status_code >= 400:
            return False, "", f"init upload HTTP {r.status_code}: {r.text[:300]}"

        upload_url = r.headers.get("location")
        if not upload_url:
            return False, "", "init upload: no Location header"

        try:
            with p.open("rb") as f:
                up = client.put(upload_url, content=f.read(), headers={"Content-Type": mime_type}, timeout=None)
        except httpx.HTTPError as e:
            return False, "", f"upload error: {e}"
        if up.status_code >= 400:
            return False, "", f"upload HTTP {up.status_code}: {up.text[:300]}"

        body = up.json()
        video_id = body.get("id")
        if not video_id:
            return False, "", f"upload: missing id ({body!r})"
        return True, video_id, ""
