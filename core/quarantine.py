"""Quarantine pipeline: untrusted content held for human review.
Downgrade-only: items never re-enter any queue automatically. Release
requires an explicit human verdict recorded with a note. Nothing here
executes, sends, or resolves anything."""
from __future__ import annotations

import json
import os
import time
import uuid

QUARANTINE = os.getenv("QUARANTINE_PATH", os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "dash", "quarantine.jsonl"))


def _load(path: str = QUARANTINE) -> list[dict]:
    out = []
    if not os.path.exists(path):
        return out
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    return out


def hold(item: dict, reasons: list[str], path: str = QUARANTINE) -> dict:
    """Hold untrusted content. Reasons required; empty reasons refused."""
    if not reasons:
        raise ValueError("quarantine requires reasons")
    q = {"id": "q-" + uuid.uuid4().hex[:12], "item": item, "reasons": reasons,
         "state": "HELD", "ts": int(time.time())}
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(q, sort_keys=True, default=str) + "\n")
    return q


def review(quarantine_id: str, verdict: str, note: str = "", path: str = QUARANTINE) -> dict:
    """Human verdict: RELEASED (back to a human, never auto-queue) or
    CONFIRMED (stays held as attack evidence). No other transitions."""
    if verdict not in ("RELEASED", "CONFIRMED"):
        raise ValueError(f"bad verdict {verdict}")
    if not note:
        raise ValueError("verdict requires a note")
    items = _load(path)
    cur = next((q for q in reversed(items) if q["id"] == quarantine_id), None)
    if cur is None:
        raise KeyError(f"unknown held item {quarantine_id}")
    if cur["state"] != "HELD":
        raise ValueError(f"already {cur['state']}")
    nxt = dict(cur, state=verdict, review_note=note, reviewed_at=int(time.time()))
    with open(path, "a") as f:
        f.write(json.dumps(nxt, sort_keys=True, default=str) + "\n")
    return nxt


def held(path: str = QUARANTINE) -> list[dict]:
    latest: dict[str, dict] = {}
    for q in _load(path):
        latest[q["id"]] = q
    return [q for q in latest.values() if q["state"] == "HELD"]
