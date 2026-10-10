"""Human confirm gate — creates a task and waits for approval.

The pipeline calls this before any publish/spend action.
Returns True only after human approves. Never bypasses.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from typing import Any

DASH_DB = os.getenv("DASH_DB", os.path.join(os.path.dirname(__file__), "..", "..", "dash", "influence.db"))


def _db():
    return sqlite3.connect(DASH_DB, timeout=30)


def create_task(action: str, payload: dict, urgency: str = "medium",
                slug: str = "oddhobb") -> dict:
    """Create a human task in the dash. Returns task dict."""
    title = f"Approve: {action} → {payload.get('channel', '?')}"
    instructions = _preview_text(action, payload)
    risk = 0.8 if action in ("spend", "ad_publish", "money_move") else 0.3
    payload_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]

    db = _db()
    try:
        cur = db.execute(
            "INSERT INTO human_actions (project_id, resource_key, title, instructions, "
            "url, estimate_seconds, priority, done, created_at) "
            "VALUES ((SELECT id FROM projects WHERE slug=? LIMIT 1), ?, ?, ?, ?, ?, ?, 0, datetime('now'))",
            (slug, f"approve-{action}-{payload_hash}", title, instructions,
             payload.get("preview_url", ""), 120, 1 if urgency == "high" else 2),
        )
        db.commit()
        task_id = cur.lastrowid
    finally:
        db.close()

    return {
        "task_id": task_id,
        "title": title,
        "instructions": instructions,
        "urgency": urgency,
        "risk": risk,
        "action": action,
        "payload_hash": payload_hash,
        "channel": payload.get("channel", ""),
        "sku": payload.get("sku", ""),
    }


def approve_task(task_id: int) -> bool:
    """Mark task done (approved)."""
    db = _db()
    try:
        db.execute(
            "UPDATE human_actions SET done=1, completed_at=datetime('now') WHERE id=?",
            (task_id,),
        )
        db.commit()
        return True
    finally:
        db.close()


def is_approved(task_id: int) -> bool:
    db = _db()
    try:
        row = db.execute("SELECT done FROM human_actions WHERE id=?", (task_id,)).fetchone()
        return bool(row and row[0])
    finally:
        db.close()


def _preview_text(action: str, payload: dict) -> str:
    ch = payload.get("channel", "?")
    sku = payload.get("sku", "")
    lines = [f"Action: {action}", f"Channel: {ch}", f"SKU: {sku}"]
    if payload.get("title"):
        lines.append(f"Title: {payload['title'][:80]}")
    if payload.get("text"):
        lines.append(f"Text: {payload['text'][:200]}")
    if payload.get("price"):
        lines.append(f"Price: {payload['price']}")
    if payload.get("image_url"):
        lines.append(f"Image: {payload['image_url'][:80]}")
    lines.append("")
    lines.append("Approve to publish. Reject to cancel.")
    return "\n".join(lines)


def wait_for_approval(task_id: int, timeout_sec: int = 3600, poll_sec: int = 5) -> bool:
    """Poll until human approves or timeout. Returns True if approved."""
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if is_approved(task_id):
            return True
        time.sleep(poll_sec)
    return False
