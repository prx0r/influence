"""Audited actions API — log, list, totals. Stdlib sqlite3 only.

Every API call in the runtime writes one row here. The dash Actions
tab reads from here. See RUNTIME.md.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("DASH_DB", os.path.join(_HERE, "..", "dash", "influence.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS actions (
  id INTEGER PRIMARY KEY,
  at TEXT NOT NULL,
  channel TEXT NOT NULL,
  action TEXT NOT NULL,
  project_id INTEGER,
  campaign TEXT,
  sku TEXT,
  cost_usd REAL DEFAULT 0,
  cost_cents INTEGER DEFAULT 0,
  external_id TEXT,
  gates_passed INTEGER DEFAULT 0,
  gates_total INTEGER DEFAULT 0,
  receipt_id TEXT,
  status TEXT DEFAULT 'UNKNOWN',
  grant_id TEXT,
  payload_hash TEXT,
  response_hash TEXT
);
CREATE INDEX IF NOT EXISTS idx_actions_at ON actions(at);
CREATE INDEX IF NOT EXISTS idx_actions_channel ON actions(channel);
CREATE INDEX IF NOT EXISTS idx_actions_campaign ON actions(campaign);
CREATE INDEX IF NOT EXISTS idx_actions_status ON actions(status);
"""


def _db(path: str = DB_PATH):
    db = sqlite3.connect(path, timeout=30)
    db.executescript(SCHEMA)
    return db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(obj) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def project_id_for(slug: str | None, db_path: str = DB_PATH) -> int | None:
    if not slug:
        return None
    db = _db(db_path)
    try:
        row = db.execute("SELECT id FROM projects WHERE slug=?", (slug,)).fetchone()
        return row[0] if row else None
    finally:
        db.close()


def log_action(channel: str, action: str, cost_usd: float = 0.0,
               sku: str | None = None, campaign: str | None = None,
               project_slug: str | None = None,
               external_id: str | None = None,
               gates_passed: int = 0, gates_total: int = 0,
               receipt_id: str | None = None,
               status: str = "UNKNOWN", grant_id: str | None = None,
               payload: dict | None = None, response: dict | None = None,
               db_path: str = DB_PATH) -> int:
    db = _db(db_path)
    try:
        pid = project_id_for(project_slug, db_path)
        cur = db.execute(
            "INSERT INTO actions (at, channel, action, project_id, campaign, sku,"
            " cost_usd, cost_cents, external_id, gates_passed, gates_total,"
            " receipt_id, status, grant_id, payload_hash, response_hash)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (_now(), channel, action, pid, campaign, sku,
             cost_usd, int(round(cost_usd * 100)), external_id,
             gates_passed, gates_total, receipt_id, status, grant_id,
             _hash(payload) if payload else None,
             _hash(response) if response else None),
        )
        db.commit()
        return cur.lastrowid
    finally:
        db.close()


def list_actions(channel: str | None = None, campaign: str | None = None,
                 status: str | None = None, limit: int = 50,
                 db_path: str = DB_PATH) -> list[dict]:
    db = _db(db_path)
    try:
        q = "SELECT id, at, channel, action, sku, campaign, cost_usd, cost_cents," \
            " external_id, gates_passed, gates_total, receipt_id, status, grant_id" \
            " FROM actions WHERE 1=1"
        args: list = []
        if channel:
            q += " AND channel=?"; args.append(channel)
        if campaign:
            q += " AND campaign=?"; args.append(campaign)
        if status:
            q += " AND status=?"; args.append(status)
        q += " ORDER BY id DESC LIMIT ?"; args.append(limit)
        rows = db.execute(q, args).fetchall()
        return [{
            "id": r[0], "at": r[1], "channel": r[2], "action": r[3],
            "sku": r[4], "campaign": r[5],
            "cost_usd": r[6], "cost_cents": r[7],
            "external_id": r[8],
            "gates": f"{r[9]}/{r[10]}",
            "receipt_id": r[11], "status": r[12], "grant_id": r[13],
        } for r in rows]
    finally:
        db.close()


def totals(campaign: str | None = None, db_path: str = DB_PATH) -> dict:
    db = _db(db_path)
    try:
        args: list = []
        wf = ""
        if campaign:
            wf = " WHERE campaign=?"; args.append(campaign)
        total, count = db.execute(
            f"SELECT COALESCE(SUM(cost_usd),0), COUNT(*) FROM actions{wf}", args).fetchone()
        by_ch = db.execute(
            f"SELECT channel, COALESCE(SUM(cost_usd),0), COUNT(*) FROM actions{wf}"
            " GROUP BY channel", args).fetchall()
        return {
            "total_usd": round(total or 0, 4),
            "count": count or 0,
            "by_channel": {ch: {"usd": round(usd or 0, 4), "count": n}
                           for ch, usd, n in by_ch},
        }
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--totals", action="store_true")
    ap.add_argument("--channel", default=None)
    ap.add_argument("--campaign", default=None)
    ap.add_argument("--status", default=None)
    ap.add_argument("--limit", type=int, default=20)
    args = ap.parse_args()
    if args.list:
        for a in list_actions(args.channel, args.campaign, args.status, args.limit):
            print(f"{a['id']:4} {(a['at'] or '?')[:19]:19} "
                  f"{a['channel']:10} {a['action'][:42]:42} "
                  f"${a['cost_usd']:.4f} {a['gates']:>5} {a['status']:7} {a['external_id'] or ''}")
    if args.totals:
        print(json.dumps(totals(args.campaign), indent=1))
