"""Google Calendar backend — OAuth, freebusy, event creation.

Per-business tokens live in the encrypted vault (platform "google"):
refresh_token, calendar_id. Availability prefers live freebusy and falls
back to scheduled-job blocks when unconnected, so slots never break.
"""
from __future__ import annotations

import json
import time
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

UA = {"User-Agent": "stevejobless-bridge/0.3"}
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
CAL_URL = "https://www.googleapis.com/calendar/v3"
SCOPES = ["https://www.googleapis.com/auth/calendar.events", "https://www.googleapis.com/auth/calendar.readonly"]


def auth_url(client_id: str, redirect_uri: str, state: str) -> str:
    return AUTH_URL + "?" + urlencode({
        "client_id": client_id, "redirect_uri": redirect_uri, "response_type": "code",
        "scope": " ".join(SCOPES), "access_type": "offline", "prompt": "consent", "state": state,
    })


def exchange_code(client_id: str, client_secret: str, redirect_uri: str, code: str) -> dict[str, Any]:
    req = Request(TOKEN_URL, data=urlencode({
        "client_id": client_id, "client_secret": client_secret, "redirect_uri": redirect_uri,
        "grant_type": "authorization_code", "code": code,
    }).encode(), headers={"Content-Type": "application/x-www-form-urlencoded", **UA}, method="POST")
    with urlopen(req, timeout=20) as resp:
        return json.loads(resp.read())


def refresh(client_id: str, client_secret: str, refresh_token: str) -> dict[str, Any]:
    req = Request(TOKEN_URL, data=urlencode({
        "client_id": client_id, "client_secret": client_secret,
        "grant_type": "refresh_token", "refresh_token": refresh_token,
    }).encode(), headers={"Content-Type": "application/x-www-form-urlencoded", **UA}, method="POST")
    with urlopen(req, timeout=20) as resp:
        return json.loads(resp.read())


def _get(access_token: str, path: str, timeout: float = 15) -> dict[str, Any]:
    req = Request(CAL_URL + path, headers={"Authorization": f"Bearer {access_token}", **UA})
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def freebusy(access_token: str, calendar_id: str, start_iso: str, end_iso: str) -> list[tuple[str, str]]:
    from datetime import datetime

    req = Request(CAL_URL + "/freeBusy", data=json.dumps({
        "timeMin": start_iso, "timeMax": end_iso, "items": [{"id": calendar_id}]}).encode(),
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json", **UA},
        method="POST")
    with urlopen(req, timeout=15) as resp:
        d = json.loads(resp.read())
    busy = ((d.get("calendars") or {}).get(calendar_id) or {}).get("busy", [])
    return [(b["start"], b["end"]) for b in busy if b.get("start") and b.get("end")]


def create_event(access_token: str, calendar_id: str, summary: str, start_iso: str, end_iso: str,
                 description: str = "", location: str = "") -> dict[str, Any]:
    req = Request(CAL_URL + f"/calendars/{calendar_id}/events", data=json.dumps({
        "summary": summary, "description": description, "location": location,
        "start": {"dateTime": start_iso}, "end": {"dateTime": end_iso}}).encode(),
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json", **UA},
        method="POST")
    with urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def with_fresh_token(vault, slug: str, client_id: str, client_secret: str) -> str | None:
    """Return a working access token (refreshing + caching for 50 min), or None."""
    cached = vault.get_credential(slug, "google", "access_token")
    exp = vault.get_credential(slug, "google", "access_expires")
    if cached and exp and float(exp) > time.time() + 60:
        return cached
    refresh_token = vault.get_credential(slug, "google", "refresh_token")
    if not refresh_token:
        return None
    d = refresh(client_id, client_secret, refresh_token)
    vault.set_credential(slug, "google", "access_token", d["access_token"])
    vault.set_credential(slug, "google", "access_expires", str(time.time() + int(d.get("expires_in", 3600))))
    return d["access_token"]
