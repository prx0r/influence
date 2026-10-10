"""Effect approval tasks + ReviewBundle. (dirs 15, 16, 17, 18)

HumanAction (done:boolean) remains for checklists/onboarding.
Consequential approvals use effect_tasks with the full state machine:

PROPOSED → REVIEW_READY → APPROVED/REJECTED → GRANTED → EXECUTING
→ VERIFYING → PROVEN_TRUE / PROVEN_FALSE / UNKNOWN_RECONCILE

Rules (frozen):
- Approval binds the exact frozen payload hash (dir 16). Never parse
  prose to recover what was approved. Grant carries the hash. Executor
  re-checks bytes before mutating. Any drift → re-review.
- APPROVED = permission to attempt, NEVER completion (dir 17). Only a
  receipt-backed verification closes the task. No human "done" clicks
  for API effects.
- ReviewBundle is immutable. CHANGE creates a new revision; approval
  never transfers across revisions.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("DASH_DB", os.path.join(_HERE, "..", "dash", "influence.db"))

STATES = ("PROPOSED", "REVIEW_READY", "APPROVED", "REJECTED", "GRANTED",
          "EXECUTING", "VERIFYING", "PROVEN_TRUE", "PROVEN_FALSE",
          "UNKNOWN_RECONCILE", "EXPIRED")

# Allowed transitions (dir 15)
TRANSITIONS = {
    "PROPOSED": ("REVIEW_READY", "REJECTED", "EXPIRED"),
    "REVIEW_READY": ("APPROVED", "REJECTED", "EXPIRED", "PROPOSED"),
    "APPROVED": ("GRANTED", "REJECTED", "EXPIRED"),
    "GRANTED": ("EXECUTING", "EXPIRED"),
    "EXECUTING": ("VERIFYING", "UNKNOWN_RECONCILE"),
    "VERIFYING": ("PROVEN_TRUE", "PROVEN_FALSE", "UNKNOWN_RECONCILE"),
    "REJECTED": ("PROPOSED",),  # re-enters, never straight to DONE
    "UNKNOWN_RECONCILE": ("EXECUTING", "REJECTED", "EXPIRED"),
    "PROVEN_TRUE": (),
    "PROVEN_FALSE": (),
    "EXPIRED": ("PROPOSED",),
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS review_bundles (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  brand TEXT NOT NULL,
  campaign TEXT,
  sku TEXT,
  source_refs_json TEXT DEFAULT '{}',
  pack_hash TEXT DEFAULT '',
  artifacts_json TEXT DEFAULT '[]',
  payload_json TEXT NOT NULL,
  payload_hash TEXT NOT NULL,
  diff_json TEXT DEFAULT '{}',
  cost_estimate_usd REAL DEFAULT 0,
  consequence_json TEXT DEFAULT '{}',
  machine_gates_json TEXT DEFAULT '[]',
  revision INTEGER DEFAULT 1,
  supersedes TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS effect_tasks (
  id INTEGER PRIMARY KEY,
  brand TEXT NOT NULL,
  kind TEXT NOT NULL,
  action_spec_id TEXT,
  review_bundle_id TEXT,
  payload_hash TEXT NOT NULL,
  risk_class TEXT DEFAULT 'medium',
  estimated_cost_usd REAL DEFAULT 0,
  cost_cap_usd REAL DEFAULT 0,
  consequence TEXT DEFAULT '',
  state TEXT DEFAULT 'PROPOSED',
  expires_at TEXT,
  decision TEXT,
  decided_at TEXT,
  decided_by TEXT DEFAULT '',
  grant_id TEXT,
  execution_id TEXT,
  receipt_id TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_effect_state ON effect_tasks(state);
CREATE INDEX IF NOT EXISTS idx_effect_brand ON effect_tasks(brand);
"""


def _db(path: str = DB_PATH):
    db = sqlite3.connect(path, timeout=30)
    db.executescript(SCHEMA)
    return db


def _sha(obj) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def _rid(prefix: str) -> str:
    return f"{prefix}_{hashlib.sha256(str(time.time_ns()).encode()).hexdigest()[:12]}"


def create_bundle(kind: str, brand: str, payload: dict,
                 campaign: str | None = None, sku: str | None = None,
                 source_refs: dict | None = None, pack_hash: str = "",
                 artifacts: list | None = None, diff: dict | None = None,
                 cost_estimate_usd: float = 0.0, consequence: dict | None = None,
                 machine_gates: list | None = None,
                 supersedes: str | None = None, revision: int = 1,
                 db_path: str = DB_PATH) -> dict:
    """Freeze an immutable ReviewBundle. Returns bundle with id + payload_hash."""
    bid = _rid("rev")
    ph = _sha(payload)
    db = _db(db_path)
    try:
        db.execute(
            "INSERT INTO review_bundles (id,kind,brand,campaign,sku,source_refs_json,"
            " pack_hash,artifacts_json,payload_json,payload_hash,diff_json,"
            " cost_estimate_usd,consequence_json,machine_gates_json,revision,supersedes)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (bid, kind, brand, campaign, sku, json.dumps(source_refs or {}),
             pack_hash, json.dumps(artifacts or []), json.dumps(payload, sort_keys=True),
             ph, json.dumps(diff or {}), cost_estimate_usd,
             json.dumps(consequence or {}), json.dumps(machine_gates or []),
             revision, supersedes))
        db.commit()
    finally:
        db.close()
    return {"id": bid, "payload_hash": ph, "revision": revision}


def get_bundle(bundle_id: str, db_path: str = DB_PATH) -> dict | None:
    db = _db(db_path)
    try:
        r = db.execute("SELECT id,kind,brand,campaign,sku,source_refs_json,pack_hash,"
                       " artifacts_json,payload_json,payload_hash,diff_json,"
                       " cost_estimate_usd,consequence_json,machine_gates_json,"
                       " revision,supersedes,created_at FROM review_bundles WHERE id=?",
                       (bundle_id,)).fetchone()
        if not r:
            return None
        return {
            "id": r[0], "kind": r[1], "brand": r[2], "campaign": r[3], "sku": r[4],
            "source_refs": json.loads(r[5] or "{}"), "pack_hash": r[6],
            "artifacts": json.loads(r[7] or "[]"), "payload": json.loads(r[8]),
            "payload_hash": r[9], "diff": json.loads(r[10] or "{}"),
            "cost_estimate_usd": r[11], "consequence": json.loads(r[12] or "{}"),
            "machine_gates": json.loads(r[13] or "[]"),
            "revision": r[14], "supersedes": r[15], "created_at": r[16],
        }
    finally:
        db.close()


def propose(brand: str, kind: str, review_bundle_id: str,
            risk_class: str = "medium", cost_cap_usd: float = 0.0,
            consequence: str = "", expires_hours: int = 48,
            db_path: str = DB_PATH) -> dict:
    """Create task in PROPOSED. Caller moves to REVIEW_READY when bundle complete."""
    b = get_bundle(review_bundle_id, db_path)
    if not b:
        raise KeyError(f"no bundle {review_bundle_id}")
    import datetime as _dt
    exp = (_dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(hours=expires_hours)).isoformat()
    db = _db(db_path)
    try:
        cur = db.execute(
            "INSERT INTO effect_tasks (brand,kind,review_bundle_id,payload_hash,"
            " risk_class,estimated_cost_usd,cost_cap_usd,consequence,state,expires_at)"
            " VALUES (?,?,?,?,?,?,?,?, 'PROPOSED', ?)",
            (brand, kind, review_bundle_id, b["payload_hash"], risk_class,
             b["cost_estimate_usd"], cost_cap_usd, consequence or kind, exp))
        db.commit()
        return {"task_id": cur.lastrowid, "state": "PROPOSED",
                "payload_hash": b["payload_hash"]}
    finally:
        db.close()


def transition(task_id: int, to_state: str, by: str = "",
               grant_id: str | None = None, execution_id: str | None = None,
               receipt_id: str | None = None, decision: str | None = None,
               db_path: str = DB_PATH) -> dict:
    """Move state. Enforces allowed transitions + hash binding on approve."""
    assert to_state in STATES, f"bad state {to_state}"
    db = _db(db_path)
    try:
        row = db.execute("SELECT state,payload_hash,review_bundle_id FROM effect_tasks"
                         " WHERE id=?", (task_id,)).fetchone()
        if not row:
            raise KeyError(f"no task {task_id}")
        cur_state = row[0]
        if to_state not in TRANSITIONS.get(cur_state, ()):
            raise ValueError(f"illegal {cur_state} → {to_state}")
        # APPROVED binds the frozen hash: re-read bundle, compare (dir 16)
        if to_state == "APPROVED":
            b = get_bundle(row[2], db_path)
            if not b or b["payload_hash"] != row[1]:
                raise ValueError("payload drift since review: re-review required")
        import datetime as _dt
        now = _dt.datetime.now(_dt.timezone.utc).isoformat()
        db.execute("UPDATE effect_tasks SET state=?,decision=COALESCE(?,decision),"
                   " decided_at=CASE WHEN ? IN ('APPROVED','REJECTED') THEN ? ELSE decided_at END,"
                   " decided_by=CASE WHEN ? IN ('APPROVED','REJECTED') THEN ? ELSE decided_by END,"
                   " grant_id=COALESCE(?,grant_id), execution_id=COALESCE(?,execution_id),"
                   " receipt_id=COALESCE(?,receipt_id), updated_at=datetime('now')"
                   " WHERE id=?",
                   (to_state, decision, to_state, now, to_state, by,
                    grant_id, execution_id, receipt_id, task_id))
        db.commit()
        return {"task_id": task_id, "state": to_state}
    finally:
        db.close()


def get_task(task_id: int, db_path: str = DB_PATH) -> dict | None:
    db = _db(db_path)
    try:
        r = db.execute("SELECT id,brand,kind,action_spec_id,review_bundle_id,payload_hash,"
                       " risk_class,estimated_cost_usd,cost_cap_usd,consequence,state,"
                       " expires_at,decision,decided_at,decided_by,grant_id,execution_id,"
                       " receipt_id,created_at FROM effect_tasks WHERE id=?",
                       (task_id,)).fetchone()
        if not r:
            return None
        keys = ("id", "brand", "kind", "action_spec_id", "review_bundle_id",
                "payload_hash", "risk_class", "estimated_cost_usd", "cost_cap_usd",
                "consequence", "state", "expires_at", "decision", "decided_at",
                "decided_by", "grant_id", "execution_id", "receipt_id", "created_at")
        return dict(zip(keys, r))
    finally:
        db.close()


def queue(brand: str | None = None, states: tuple = ("PROPOSED", "REVIEW_READY"),
          db_path: str = DB_PATH) -> list[dict]:
    """What needs judgment — the dash home view. (dir 37)"""
    db = _db(db_path)
    try:
        q = ("SELECT id,brand,kind,payload_hash,risk_class,estimated_cost_usd,"
             " consequence,state,expires_at,review_bundle_id,created_at"
             " FROM effect_tasks WHERE state IN (%s)" % ",".join("?" * len(states)))
        args: list = list(states)
        if brand:
            q += " AND brand=?"; args.append(brand)
        q += " ORDER BY CASE risk_class WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, created_at"
        cols = ("id", "brand", "kind", "payload_hash", "risk_class",
                "estimated_cost_usd", "consequence", "state", "expires_at",
                "review_bundle_id", "created_at")
        return [dict(zip(cols, r)) for r in db.execute(q, args).fetchall()]
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue", action="store_true")
    ap.add_argument("--brand", default=None)
    args = ap.parse_args()
    if args.queue:
        for t in queue(args.brand):
            print(f"{t['id']} [{t['risk_class']:6}] {t['brand']:12} {t['kind']:20} "
                  f"{t['state']:12} ${t['estimated_cost_usd']:.2f} {t['consequence'][:50]}")
