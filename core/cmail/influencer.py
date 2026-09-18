"""Influencer passport shape. New code: ordered resources + stage derivation. Statuses still come from reconcile."""
from __future__ import annotations

from typing import Any


def _checklist(label: str, title: str, instructions: str, done: bool = False,
               priority: int = 60) -> dict[str, Any]:
    return {"kind": "static", "label": label,
            "desired": {"label": label, "done": done, "executor": "HUMAN",
                        "human_title": title, "instructions": instructions, "priority": priority}}


def influencer_passport(handle: str, domain: str, done: dict[str, bool] | None = None) -> dict[str, Any]:
    """Ordered onboarding chain. done maps resource key -> checklist complete (human-marked)."""
    done = done or {}
    resources = [
        {"key": "name", **_checklist("Handle + domain picked", f"Pick handle + domain ({handle} / {domain})",
            "Choose the canonical handle and domain, then record them here.", done.get("name", True))},
        {"key": "handles", **_checklist("Handles mapped", f"Map handles for {handle}",
            "Map the handle across x, instagram, tiktok. Record availability proof.", priority=55)},
        {"key": "domain", "kind": "domain", "label": "Domain owned",
         "desired": {"domain": domain}},
        {"key": "registrar", "kind": "registrar", "label": "Registration verified",
         "desired": {"domain": domain}},
        {"key": "zone", "kind": "website", "label": "Zone + site live",
         "desired": {"url": f"https://{domain}"}},
        {"key": "mailbox", "kind": "mail", "label": "Mailbox live",
         "desired": {"domain": domain}},
        {"key": "number", "kind": "number", "label": "Number provisioned",
         "desired": {"capabilities": ["sms_in"], "max_class": "PSEUDONYMOUS_BRIDGE"}},
        {"key": "social:x", "kind": "social", "label": "X connected",
         "desired": {"platform": "x", "handle": handle}},
        {"key": "content", **_checklist("First week queued", f"Queue first week for {handle}",
            "Draft 7 posts. Drafts only, publishing stays gated.", priority=40)},
    ]
    for r in resources:
        if r["key"] in done:
            r["desired"]["done"] = done[r["key"]]
    return {"version": 1, "influencer": {"handle": handle, "domain": domain}, "resources": resources}


def derive_stage(states: dict[str, str]) -> str:
    """Stage from resource statuses. Mirrors seed stages so dash stays stable across the port."""
    if states.get("content") == "READY":
        return "live"
    if states.get("mailbox") == "READY" or states.get("social:x") == "READY":
        return "wired-needs-content"
    if states.get("domain") == "READY":
        return "domain-owned"
    if states.get("name") == "READY":
        return "name-only"
    return "untouched"
