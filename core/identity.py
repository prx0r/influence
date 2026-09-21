"""Identity registry — permanent, append-only identity slots.

An identity is a resolved function chain (dependency-graph.md L7).
It owns: domain, email, phone, socials, website.
Each slot is a ResourceState with status + metadata + receipt history.

Design principles (from AGENTS.md):
- Permanent: never delete, only append
- Receipt-backed: every slot change emits a receipt
- Human-gated: L2 slots (domain, phone, socials) require human approval
- Machine-readable: JSON schema, versioned
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# Slot definitions — what each identity owns
SLOT_DEFS = {
    "domain": {
        "label": "Domain",
        "icon": "globe",
        "fields": ["name", "registrar", "nameservers", "cloudflare_zone_id", "expires_at"],
        "gate": "human",  # requires human to buy
    },
    "email": {
        "label": "Email",
        "icon": "mail",
        "fields": ["address", "provider", "routing_target", "verified_at"],
        "gate": "machine",  # can auto-configure via API
    },
    "phone": {
        "label": "Phone",
        "icon": "phone",
        "fields": ["number", "provider", "connection_id", "messaging_profile_id", "sms_verified", "voice_verified"],
        "gate": "human",  # requires human to buy
    },
    "twitter": {
        "label": "Twitter/X",
        "icon": "twitter",
        "fields": ["handle", "claimed_at", "posting_enabled"],
        "gate": "human",
    },
    "github": {
        "label": "GitHub",
        "icon": "github",
        "fields": ["org", "repos", "claimed_at"],
        "gate": "human",
    },
    "youtube": {
        "label": "YouTube",
        "icon": "youtube",
        "fields": ["channel_id", "channel_name", "subscribers"],
        "gate": "human",
    },
    "telegram": {
        "label": "Telegram",
        "icon": "telegram",
        "fields": ["channel", "members", "claimed_at"],
        "gate": "human",
    },
    "website": {
        "label": "Website",
        "icon": "layout",
        "fields": ["url", "status_code", "deployed_at", "framework"],
        "gate": "machine",
    },
}


class Identity:
    """A permanent identity with versioned slot states."""

    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, slug: str) -> Path:
        return self.data_dir / f"{slug}.json"

    def create(self, slug: str, name: str, category: str = "",
               niche: str = "", tagline: str = "") -> dict:
        """Create a new identity. Never overwrites existing."""
        path = self._path(slug)
        if path.exists():
            return self.get(slug)

        identity = {
            "slug": slug,
            "name": name,
            "category": category,
            "niche": niche,
            "tagline": tagline,
            "created_at": utcnow(),
            "slots": {},
            "receipts": [],
        }
        # Initialize all slots as pending
        for slot_id, slot_def in SLOT_DEFS.items():
            identity["slots"][slot_id] = {
                "status": "pending",
                "fields": {},
                "updated_at": utcnow(),
                "receipts": [],
            }

        path.write_text(json.dumps(identity, indent=2, default=str))
        self._emit_receipt(slug, "identity.created", {"slug": slug, "name": name})
        return identity

    def get(self, slug: str) -> dict | None:
        path = self._path(slug)
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def list_all(self) -> list[dict]:
        identities = []
        for p in sorted(self.data_dir.glob("*.json")):
            try:
                identities.append(json.loads(p.read_text()))
            except:
                continue
        return identities

    def update_slot(self, slug: str, slot_id: str, fields: dict,
                    status: str | None = None) -> dict:
        """Update a slot's fields. Appends receipt."""
        identity = self.get(slug)
        if not identity:
            raise ValueError(f"identity {slug} not found")
        if slot_id not in SLOT_DEFS:
            raise ValueError(f"unknown slot {slot_id}")

        slot = identity["slots"][slot_id]
        slot["fields"].update(fields)
        if status:
            slot["status"] = status
        slot["updated_at"] = utcnow()

        receipt = self._emit_receipt(slug, f"slot.{slot_id}.updated",
                                     {"slot": slot_id, "fields": fields, "status": status})
        slot["receipts"].append(receipt)
        identity["receipts"].append(receipt)

        self._save(identity)
        return identity

    def set_slot_status(self, slug: str, slot_id: str, status: str) -> dict:
        """Set slot status (pending/ready/error). Appends receipt."""
        identity = self.get(slug)
        if not identity:
            raise ValueError(f"identity {slug} not found")

        old_status = identity["slots"][slot_id]["status"]
        identity["slots"][slot_id]["status"] = status
        identity["slots"][slot_id]["updated_at"] = utcnow()

        receipt = self._emit_receipt(slug, f"slot.{slot_id}.status",
                                     {"slot": slot_id, "from": old_status, "to": status})
        identity["slots"][slot_id]["receipts"].append(receipt)
        identity["receipts"].append(receipt)

        self._save(identity)
        return identity

    def get_status(self, slug: str) -> dict:
        """Get summary status: ready/total/online."""
        identity = self.get(slug)
        if not identity:
            return {"error": f"identity {slug} not found"}

        ready = sum(1 for s in identity["slots"].values() if s["status"] == "ready")
        total = len(identity["slots"])
        return {
            "slug": slug,
            "name": identity["name"],
            "ready": ready,
            "total": total,
            "online": ready == total,
            "slots": {sid: {"status": s["status"], "fields": s["fields"]}
                      for sid, s in identity["slots"].items()},
        }

    def _emit_receipt(self, slug: str, event: str, data: dict) -> dict:
        return {
            "event": event,
            "slug": slug,
            "data": data,
            "timestamp": utcnow(),
            "hash": hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()[:16],
        }

    def _save(self, identity: dict):
        self._path(identity["slug"]).write_text(
            json.dumps(identity, indent=2, default=str))
