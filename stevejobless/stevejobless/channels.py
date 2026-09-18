"""Meta WhatsApp Cloud API + SMS adapters.

Tradies live on WhatsApp, so this is native, not an afterthought.
Creds needed (vault `oracle` — NOT present yet, stub mode until added):
  WHATSAPP_TOKEN, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_VERIFY_TOKEN
  SMS_PROVIDER_TOKEN (Twilio/Telnyx — pick one when wiring SMS confirm)
Until creds exist every send is logged + returned as stubbed, so all
workflows above are fully testable today.
"""
from __future__ import annotations

import os
from typing import Any
from urllib.request import Request, urlopen
import json


def whatsapp_configured() -> bool:
    return bool(os.getenv("WHATSAPP_TOKEN") and os.getenv("WHATSAPP_PHONE_NUMBER_ID"))


def send_whatsapp(to: str, text: str) -> dict[str, Any]:
    if not whatsapp_configured():
        return {"ok": True, "stubbed": True, "to": to, "text": text[:200],
                "note": "set WHATSAPP_TOKEN + WHATSAPP_PHONE_NUMBER_ID for live sends"}
    url = f"https://graph.facebook.com/v21.0/{os.getenv('WHATSAPP_PHONE_NUMBER_ID')}/messages"
    req = Request(url, data=json.dumps({
        "messaging_product": "whatsapp", "to": to,
        "type": "text", "text": {"body": text},
    }).encode(), headers={"Authorization": f"Bearer {os.getenv('WHATSAPP_TOKEN')}",
                           "Content-Type": "application/json",
                           "User-Agent": "stevejobless-bridge/0.3"}, method="POST")
    with urlopen(req, timeout=20) as resp:
        return {"ok": True, "stubbed": False, "result": json.loads(resp.read())}


def send_sms(to: str, text: str, api_key: str | None = None,
             from_number: str | None = None, profile_id: str | None = None) -> dict[str, Any]:
    """SMS confirm path. With Telnyx creds → real delivery; else honest stub."""
    key = api_key or os.getenv("TELNYX_API_KEY", "")
    sender = from_number or os.getenv("TELNYX_PHONE_NUMBER", "")
    if key and sender:
        from . import telephony

        try:
            return telephony.send_sms(key, sender, to, text, profile_id or os.getenv("TELNYX_MESSAGING_PROFILE_ID"))
        except Exception as e:
            return {"ok": False, "stubbed": False, "error": str(e)[:200]}
    return {"ok": True, "stubbed": True, "to": to, "text": text[:200],
            "note": "SMS provider not wired — save Telnyx key via /backend/{slug}/telnyx/credential"}


def parse_whatsapp_webhook(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten Meta webhook → [{from, text, timestamp}]. Voice-agent and steve share this."""
    out = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            for msg in change.get("value", {}).get("messages", []):
                if msg.get("type") == "text":
                    out.append({"from": msg.get("from", ""), "text": msg.get("text", {}).get("body", ""),
                                "timestamp": msg.get("timestamp", "")})
    return out


def parse_instagram_webhook(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten IG messaging webhook → [{from, text}]. Customer must message first (Meta rule)."""
    out = []
    for entry in payload.get("entry", []):
        for item in entry.get("messaging", []):
            msg = item.get("message", {})
            text = msg.get("text", "")
            sender = str((item.get("sender") or {}).get("id", ""))
            if text and not msg.get("is_echo"):
                out.append({"from": f"ig:{sender}", "text": text})
    return out


def send_instagram(recipient_ig_id: str, text: str, page_token: str | None = None) -> dict[str, Any]:
    """IG DM send. Needs per-business page token in vault (platform instagram).
    24h window + no unsolicited promo per Meta rules — callers must reply, never blast."""
    if not page_token:
        return {"ok": True, "stubbed": True, "to": recipient_ig_id, "text": text[:200],
                "note": "no instagram page_token — connect via SKILL.md"}
    req = Request(f"https://graph.facebook.com/v21.0/me/messages",
                  data=json.dumps({"recipient": {"id": recipient_ig_id},
                                   "message": {"text": text}}).encode(),
                  headers={"Authorization": f"Bearer {page_token}",
                           "Content-Type": "application/json",
                           "User-Agent": "stevejobless-bridge/0.3"}, method="POST")
    with urlopen(req, timeout=20) as resp:
        return {"ok": True, "stubbed": False, "result": json.loads(resp.read())}
