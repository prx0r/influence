"""Telnyx backend — numbers, call-control webhooks, SMS, call events.

The voice side (LiveKit agent) handles audio. This side owns the account:
provisioning numbers, pointing webhooks at the brain, turning completed
calls into jobs, and sending SMS (confirmations, on-my-way) with real
delivery once creds exist. Without creds every call degrades to stubs,
so the whole flow is testable today.

Vault layout (platform "telnyx"): api_key, connection_id (call control app),
phone_number, messaging_profile_id.
"""
from __future__ import annotations

import json
from typing import Any
from urllib.request import Request, urlopen

API = "https://api.telnyx.com/v2"
UA = {"User-Agent": "stevejobless-bridge/0.3"}


class TelnyxError(Exception):
    pass


def _call(api_key: str, method: str, path: str, body: dict | None = None, timeout: float = 20) -> dict[str, Any]:
    req = Request(API + path,
                  data=json.dumps(body).encode() if body is not None else None,
                  headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", **UA},
                  method=method)
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read() or b"{}")
    except Exception as e:
        # surface Telnyx's error body when available
        detail = getattr(e, "read", lambda: b"")() if hasattr(e, "read") else b""
        raise TelnyxError(f"{method} {path}: {e} {detail[:200]!r}")


def list_numbers(api_key: str) -> list[dict[str, Any]]:
    d = _call(api_key, "GET", "/phone_numbers?page[size]=100")
    return [{"number": n.get("phone_number"), "connection": (n.get("connection_id") or "")[:8]}
            for n in d.get("data", [])]


def search_numbers(api_key: str, country: str = "GB", limit: int = 5) -> list[dict[str, Any]]:
    d = _call(api_key, "GET", f"/available_phone_numbers?filter[country_code]={country}&page[size]={limit}")
    return [{"number": n.get("phone_number"), "features": n.get("features", [])} for n in d.get("data", [])]


def set_voice_webhook(api_key: str, connection_id: str, webhook_url: str) -> dict[str, Any]:
    """Point a Call Control app at the brain. Returns the updated app."""
    d = _call(api_key, "PATCH", f"/call_control_applications/{connection_id}",
              {"webhook_event_url": webhook_url, "webhook_event_failover_url": webhook_url})
    return d.get("data", {})


def send_sms(api_key: str, from_number: str, to: str, text: str,
             profile_id: str | None = None) -> dict[str, Any]:
    body = {"from": from_number, "to": to, "text": text}
    if profile_id:
        body["messaging_profile_id"] = profile_id
    d = _call(api_key, "POST", "/messages", body)
    return {"ok": True, "stubbed": False, "id": (d.get("data") or {}).get("id")}


def parse_call_event(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Normalize Telnyx CallControl webhooks → brain event. Returns None for
    uninteresting events (heartbeat/noise)."""
    etype = payload.get("data", {}).get("event_type", "")
    p = payload.get("data", {}).get("payload", {})
    interesting = {
        "call.initiated": "started",
        "call.answered": "answered",
        "call.hangup": "completed",
        "call.recording.saved": "recording",
        "call.transcription": "transcript",
    }
    if etype not in interesting:
        return None
    return {
        "kind": interesting[etype],
        "call_id": p.get("call_control_id") or p.get("call_leg_id", ""),
        "from": p.get("from", ""),
        "to": p.get("to", ""),
        "duration_sec": p.get("call_duration_secs"),
        "recording_url": p.get("recording_urls", {}).get("mp3") if isinstance(p.get("recording_urls"), dict) else None,
        "transcript": p.get("transcription_text") or p.get("transcript"),
        "hangup_cause": p.get("hangup_cause"),
    }


def parse_sms_event(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Normalize Telnyx inbound SMS webhooks → {from, to, text}."""
    d = payload.get("data", {})
    if d.get("event_type") != "message.received":
        return None
    p = d.get("payload", {})
    text = p.get("text", "")
    if not text:
        return None
    return {"from": p.get("from", {}).get("phone_number", ""), "to": p.get("to", {}).get("phone_number", ""),
            "text": text}
