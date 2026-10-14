"""Studio human-approval grants — the dash "Approve & render" button.

The human pressing approve on an exact quoted payload IS the authority.
Grants are: bound to one payload hash, single-use, 10-minute expiry.
runtime.execute re-verifies hash + expiry before any credit burns.

File lives in dash/ (gitignored) so a restart doesn't resurrect spent grants.
"""
from __future__ import annotations

import hashlib
import json
import os
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
STORE = os.path.join(_HERE, "studio_grants.json")
TTL = 600  # 10 minutes


def _load() -> dict:
    try:
        with open(STORE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(d: dict) -> None:
    tmp = STORE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f)
    os.chmod(tmp, 0o600)
    os.replace(tmp, STORE)


def _payload_hash(payload: dict) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def issue(action: str, payload: dict, approved_by: str = "dash-human") -> dict:
    """Mint a single-use grant for an exact payload. Call ONLY from an
    authenticated human-approve handler (dash token gate)."""
    h = _payload_hash(payload)
    gid = "sg_" + hashlib.sha256(
        f"{h}{time.time()}".encode()).hexdigest()[:16]
    d = _load()
    # prune expired
    now = int(time.time())
    d = {k: v for k, v in d.items() if v.get("expires_at", 0) > now}
    d[gid] = {"action": action, "payload_hash": h,
              "expires_at": now + TTL, "used": False,
              "approved_by": approved_by, "issued_at": now}
    _save(d)
    return {"grant_id": gid, "action": action, "payload_hash": h,
            "expires_at": now + TTL}


def redeem(grant_id: str) -> dict | None:
    """Single-use redeem → returns the runtime.execute-shaped grant, or None.
    Marks used BEFORE returning so a crash can't double-spend."""
    d = _load()
    g = d.get(grant_id)
    if not g or g.get("used"):
        return None
    if g.get("expires_at", 0) < int(time.time()):
        return None
    g["used"] = True
    _save(d)
    return {"action": g["action"], "payload_hash": g["payload_hash"],
            "expires_at": g["expires_at"]}
