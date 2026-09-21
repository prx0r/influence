"""Identity-scoped store — each identity gets its own DB + receipts + agents.

Architecture:
  identities/{slug}/
  ├── identity.json       # slots, metadata, receipt history
  ├── influence.db        # scoped SQLite (jobs, decisions, effects)
  ├── receipts.jsonl      # receipt log (append-only)
  ├── rewards.jsonl       # reward log
  └── agents/             # agent action history

The dash code becomes a template: same structure, different data per identity.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class IdentityStore:
    """Scoped store for one identity."""

    def __init__(self, identities_dir: str | Path, slug: str):
        self.identities_dir = Path(identities_dir)
        self.slug = slug
        self.base = self.identities_dir / slug
        self.base.mkdir(parents=True, exist_ok=True)
        (self.base / "agents").mkdir(exist_ok=True)

    @property
    def db_path(self) -> str:
        return str(self.base / "influence.db")

    @property
    def receipts_path(self) -> str:
        return str(self.base / "receipts.jsonl")

    @property
    def rewards_path(self) -> str:
        return str(self.base / "rewards.jsonl")

    @property
    def identity_path(self) -> str:
        return str(self.base / "identity.json")

    def load_identity(self) -> dict | None:
        if not os.path.exists(self.identity_path):
            return None
        return json.loads(Path(self.identity_path).read_text())

    def save_identity(self, data: dict):
        Path(self.identity_path).write_text(json.dumps(data, indent=2, default=str))

    def append_receipt(self, receipt: dict):
        """Append receipt to log. Never overwrites."""
        with open(self.receipts_path, "a") as f:
            f.write(json.dumps(receipt, default=str) + "\n")

    def append_reward(self, reward: dict):
        with open(self.rewards_path, "a") as f:
            f.write(json.dumps(reward, default=str) + "\n")

    def read_receipts(self) -> list[dict]:
        if not os.path.exists(self.receipts_path):
            return []
        receipts = []
        for line in Path(self.receipts_path).read_text().splitlines():
            if line.strip():
                try:
                    receipts.append(json.loads(line))
                except:
                    continue
        return receipts

    def append_agent_action(self, action: dict):
        """Log agent action with timestamp."""
        from datetime import datetime, timezone
        action["timestamp"] = datetime.now(timezone.utc).isoformat()
        path = self.base / "agents" / "actions.jsonl"
        with open(path, "a") as f:
            f.write(json.dumps(action, default=str) + "\n")

    def read_agent_actions(self, limit: int = 50) -> list[dict]:
        path = self.base / "agents" / "actions.jsonl"
        if not path.exists():
            return []
        actions = []
        for line in path.read_text().splitlines():
            if line.strip():
                try:
                    actions.append(json.loads(line))
                except:
                    continue
        return actions[-limit:]

    def get_status(self) -> dict:
        """Summary: receipts count, agent actions, identity status."""
        identity = self.load_identity()
        receipts = self.read_receipts()
        actions = self.read_agent_actions()
        return {
            "slug": self.slug,
            "identity": identity,
            "receipts": len(receipts),
            "agent_actions": len(actions),
            "last_action": actions[-1] if actions else None,
            "last_receipt": receipts[-1] if receipts else None,
        }


class IdentityRegistry:
    """Top-level registry: manages all identity stores."""

    def __init__(self, identities_dir: str | Path):
        self.identities_dir = Path(identities_dir)
        self.identities_dir.mkdir(parents=True, exist_ok=True)

    def get(self, slug: str) -> IdentityStore:
        return IdentityStore(self.identities_dir, slug)

    def list_slugs(self) -> list[str]:
        return [d.name for d in self.identities_dir.iterdir()
                if d.is_dir() and (d / "identity.json").exists()]

    def list_all(self) -> list[dict]:
        stores = []
        for slug in self.list_slugs():
            store = self.get(slug)
            identity = store.load_identity()
            if identity:
                stores.append({
                    "slug": slug,
                    "name": identity.get("name", slug),
                    "category": identity.get("category", ""),
                    "status": store.get_status(),
                })
        return stores
