"""Bluesky adapter — AT Protocol (no OAuth, just app password)."""
from __future__ import annotations

import httpx

platform = "bluesky"

PDS_URL = "https://bsky.social"


def publish(content: str, media_urls: list[str] | None = None,
            settings: dict | None = None, account_extra: dict | None = None) -> tuple[bool, str, str]:
    extra = account_extra or {}
    handle = extra.get("handle", "")
    app_password = extra.get("app_password", "")
    pds = extra.get("pds_url", PDS_URL)

    if not (handle and app_password):
        return False, "", "BLUESKY_HANDLE / APP_PASSWORD missing"

    try:
        with httpx.Client() as client:
            auth_r = client.post(f"{pds}/xrpc/com.atproto.server.createSession", json={
                "identifier": handle, "password": app_password,
            }, timeout=15)
            if auth_r.status_code >= 400:
                return False, "", f"bluesky auth: {auth_r.status_code} {auth_r.text[:300]}"

            session = auth_r.json()
            access_jwt = session.get("accessJwt", "")
            did = session.get("did", "")

            record = {
                "$type": "app.bsky.feed.post",
                "text": content[:300],
                "createdAt": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            }

            r = client.post(f"{pds}/xrpc/com.atproto.repo.createRecord", headers={
                "Authorization": f"Bearer {access_jwt}",
            }, json={"repo": did, "collection": "app.bsky.feed.post", "record": record}, timeout=15)

            if r.status_code >= 400:
                return False, "", f"bluesky post: {r.status_code} {r.text[:300]}"

            cid = r.json().get("cid", "")
            return True, cid, ""
    except Exception as e:
        return False, "", f"bluesky error: {e}"
