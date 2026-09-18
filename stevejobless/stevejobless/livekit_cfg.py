"""LiveKit backend config — the handoff the voice agent consumes.

We don't run the agent; we generate its exact SIP wiring (Telnyx → LiveKit
SIP trunk + dispatch rule) and validate it, so the voice side is config-only.
Patterns mirror LiveKit's outbound-caller/session model; values are ours.
"""
from __future__ import annotations

from typing import Any


def sip_trunk_config(phone_number: str, livekit_sip_host: str, trunk_name: str = "telnyx-inbound",
                     agent_name: str = "sparky-voice") -> dict[str, Any]:
    """Config the voice agent applies to its LiveKit project for one number."""
    return {
        "trunk": {
            "name": trunk_name,
            "numbers": [phone_number],
            "allowed_addresses": [],  # Telnyx SIP IPs — fill from Telnyx docs at setup
            "auth": {"username": f"{trunk_name}-user", "password": "<set-at-setup>"},
        },
        "dispatch_rule": {
            "type": "direct",
            "room_prefix": f"call-{agent_name}",
            "agent_name": agent_name,
        },
        "inbound": {
            "provider": "telnyx",
            "telnyx_sip_destination": f"sip:{livekit_sip_host};transport=tcp",
            "note": "In Telnyx portal: SIP connection → outbound voice profile → "
                    f"SIP URI {livekit_sip_host}. Inbound calls route Telnyx → LiveKit → agent.",
        },
        "egress": {
            "recording": True,
            "transcription": True,
            "webhook": "{brain}/api/backend/telnyx/voice-webhook?slug={slug}",
            "note": "Recording+transcript URLs land on the job via the brain webhook.",
        },
    }


def validate_sip_config(cfg: dict[str, Any]) -> list[str]:
    """Missing-field report for reconcile. Empty = ready."""
    problems = []
    trunk = cfg.get("trunk", {})
    if not trunk.get("numbers"):
        problems.append("no phone numbers on trunk — buy/provision one in Telnyx first")
    if "<set-at-setup>" in str(trunk.get("auth", {}).get("password", "")):
        problems.append("trunk auth password is a placeholder")
    if not trunk.get("allowed_addresses"):
        problems.append("no allowed SIP addresses — trunk accepts from anywhere until set")
    if "{brain}" in str(cfg.get("egress", {}).get("webhook", "")):
        problems.append("egress webhook still templated — set the brain base URL")
    return problems
