"""Entity goals — A-goal registries per brand/supplier. Stdlib sqlite3 only.

A-goal → A-tasks → A-logs → A-proof → DONE.
Goal DONE is DERIVED from tasks, never stored.
See docs/pipeline/ENTITY-GOALS.md + qprivately/docs/ATASK.md.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("DASH_DB", os.path.join(_HERE, "..", "dash", "influence.db"))

STATUSES = ("PROPOSED", "JUSTIFIED", "EXECUTING", "REPORTED", "DONE",
            "PAUSED", "REJECTED", "FAILED")

SCHEMA = """
CREATE TABLE IF NOT EXISTS goals (
  id INTEGER PRIMARY KEY,
  entity TEXT NOT NULL,              -- brand:oddhobb | supplier:jlc
  title TEXT NOT NULL,
  acceptance_json TEXT DEFAULT '[]', -- numbered checkable indices
  priority TEXT DEFAULT 'P1',        -- P0 | P1 | P2 | P3
  deadline TEXT,
  notes TEXT DEFAULT '',
  created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS goal_tasks (
  id INTEGER PRIMARY KEY,
  goal_id INTEGER,
  covers_json TEXT DEFAULT '[]',     -- acceptance indices this task covers
  title TEXT NOT NULL,
  acceptance TEXT DEFAULT '',
  evidence_required TEXT DEFAULT '',
  status TEXT DEFAULT 'PROPOSED',
  receipt_id TEXT,
  human_task_id INTEGER,             -- links to human_actions when PAUSED
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (goal_id) REFERENCES goals(id)
);
CREATE INDEX IF NOT EXISTS idx_goals_entity ON goals(entity);
CREATE INDEX IF NOT EXISTS idx_gtasks_goal ON goal_tasks(goal_id);
"""


def _db(path: str = DB_PATH):
    db = sqlite3.connect(path, timeout=30)
    db.executescript(SCHEMA)
    return db


def create_goal(entity: str, title: str, acceptance: list[str],
                priority: str = "P1", deadline: str | None = None,
                notes: str = "", db_path: str = DB_PATH) -> int:
    assert acceptance, "goal needs checkable acceptance (ATASK: refused otherwise)"
    db = _db(db_path)
    try:
        cur = db.execute(
            "INSERT INTO goals (entity,title,acceptance_json,priority,deadline,notes)"
            " VALUES (?,?,?,?,?,?)",
            (entity, title, json.dumps(acceptance), priority, deadline, notes))
        db.commit()
        return cur.lastrowid
    finally:
        db.close()


def add_task(goal_id: int, covers: list[int], title: str,
             acceptance: str = "", evidence_required: str = "",
             db_path: str = DB_PATH) -> int:
    assert acceptance and evidence_required, "task needs acceptance + evidence (ATASK)"
    db = _db(db_path)
    try:
        cur = db.execute(
            "INSERT INTO goal_tasks (goal_id,covers_json,title,acceptance,evidence_required)"
            " VALUES (?,?,?,?,?)",
            (goal_id, json.dumps(covers), title, acceptance, evidence_required))
        db.commit()
        return cur.lastrowid
    finally:
        db.close()


def set_task_status(task_id: int, status: str, receipt_id: str | None = None,
                    human_task_id: int | None = None,
                    db_path: str = DB_PATH) -> None:
    assert status in STATUSES, f"bad status {status}"
    db = _db(db_path)
    try:
        if receipt_id:
            db.execute("UPDATE goal_tasks SET status=?,receipt_id=?,updated_at=datetime('now')"
                       " WHERE id=?", (status, receipt_id, task_id))
        elif human_task_id:
            db.execute("UPDATE goal_tasks SET status=?,human_task_id=?,updated_at=datetime('now')"
                       " WHERE id=?", (status, human_task_id, task_id))
        else:
            db.execute("UPDATE goal_tasks SET status=?,updated_at=datetime('now')"
                       " WHERE id=?", (status, task_id))
        db.commit()
    finally:
        db.close()


def goal_status(goal_id: int, db_path: str = DB_PATH) -> dict:
    """DERIVED status — never stored. DONE iff every acceptance index has a DONE task."""
    db = _db(db_path)
    try:
        g = db.execute("SELECT entity,title,acceptance_json,priority,deadline"
                       " FROM goals WHERE id=?", (goal_id,)).fetchone()
        if not g:
            raise KeyError(f"no goal {goal_id}")
        acceptance = json.loads(g[2] or "[]")
        tasks = [{
            "id": r[0], "covers": json.loads(r[1] or "[]"), "title": r[2],
            "status": r[3], "receipt_id": r[4],
        } for r in db.execute(
            "SELECT id,covers_json,title,status,receipt_id FROM goal_tasks"
            " WHERE goal_id=? ORDER BY id", (goal_id,)).fetchall()]
        covered = set()
        for t in tasks:
            if t["status"] == "DONE":
                covered.update(t["covers"])
        needed = set(range(len(acceptance)))
        done = needed and needed <= covered
        # count by status
        by_status: dict[str, int] = {}
        for t in tasks:
            by_status[t["status"]] = by_status.get(t["status"], 0) + 1
        return {
            "id": goal_id, "entity": g[0], "title": g[1],
            "acceptance": acceptance, "priority": g[3], "deadline": g[4],
            "derived": "DONE" if done else "OPEN",
            "covered": sorted(covered), "needed": sorted(needed),
            "tasks": tasks, "by_status": by_status,
        }
    finally:
        db.close()


def list_goals(entity: str | None = None, db_path: str = DB_PATH) -> list[dict]:
    db = _db(db_path)
    try:
        q = "SELECT id,entity,title,acceptance_json,priority,deadline FROM goals"
        args: list = []
        if entity:
            q += " WHERE entity=?"; args.append(entity)
        q += " ORDER BY priority, id"
        out = []
        for r in db.execute(q, args).fetchall():
            st = goal_status(r[0], db_path)
            out.append({
                "id": r[0], "entity": r[1], "title": r[2],
                "acceptance_n": len(json.loads(r[3] or "[]")),
                "priority": r[4], "deadline": r[5],
                "derived": st["derived"],
                "by_status": st["by_status"],
                "covered": f"{len(st['covered'])}/{len(st['needed'])}",
            })
        return out
    finally:
        db.close()


def seed_q4(db_path: str = DB_PATH) -> list[int]:
    """Seed Q4 OddHobb goals from docs/Q4-ODDHOBB.md. Idempotent-ish (checks title)."""
    db = _db(db_path)
    try:
        existing = {r[0] for r in db.execute("SELECT title FROM goals").fetchall()}
    finally:
        db.close()
    ids = []

    def _maybe(entity, title, acceptance, priority, deadline, tasks):
        if title in existing:
            return None
        gid = create_goal(entity, title, acceptance, priority, deadline, db_path=db_path)
        for covers, ttitle, tacc, tev in tasks:
            tid = add_task(gid, covers, ttitle, tacc, tev, db_path=db_path)
            _ = tid
        ids.append(gid)
        return gid

    # Q4-001 catalogue
    _maybe("brand:oddhobb", "Q4: catalogue excellent (5-8 listings)",
           ["5+ listings have real product imagery",
            "all listings have dims + materials + personalisation",
            "delivery estimates honest (match Prodigi windows)",
            "pricing includes real manufacturing costs"],
           "P0", "2026-10-24", [
               ([0, 1], "Halloween + Xmas cards: full listing pass",
                "both listings have title/tags/desc/materials/personalisation",
                "etsy GET showing fields + receipt"),
               ([2, 3], "Prodigi spec alignment on card listings",
                "materials=330gsm Fedrigoni, delivery windows in copy",
                "etsy GET + Prodigi quote"),
               ([0, 1, 2, 3], "3-6 more listings to excellent standard",
                "each passes the same listing checklist",
                "etsy GET per listing + receipts"),
           ])
    # Q4-002 buying journey
    _maybe("brand:oddhobb", "Q4: buying journey works end-to-end",
           ["customer can configure from Etsy listing",
            "payment + order storage + address verified",
            "photos submitted and correct design returned",
            "fulfilment path confirmed"],
           "P0", "2026-10-24", [
               ([0, 1, 2, 3], "Dry-run one card order end-to-end",
                "test order completes without manual fixes",
                "order receipt + fulfilment confirmation"),
           ])
    # Q4-003 distribution
    _maybe("brand:oddhobb", "Q4: distribution experiment live",
           ["Pinterest organic pins publishing",
            "one paid channel capped and running",
            "pins link to purchase-ready products"],
           "P0", "2026-10-31", [
               ([0, 2], "Pinterest pins for top 5 listings",
                "5 pins live, linked to listings",
                "pin URLs + receipts"),
               ([1], "Etsy Ads capped test on strongest 3",
                "ads running with daily cap, tracking on",
                "ads dashboard screenshot + spend log"),
           ])
    # Q4-004 demand loop
    _maybe("brand:oddhobb", "Q4: demand review loop running",
           ["weekly review of searches/clicks/saves/buys",
            "variations launched from findings"],
           "P1", None, [
               ([0], "First demand review (week 1)",
                "review doc with top searches + actions",
                "review doc + receipts"),
           ])
    # Q4-005 suppliers
    _maybe("brand:oddhobb", "Q4: supplier outreach (JLC + warehouse)",
           ["JLC API application submitted + prototype ordered",
            "warehouse pilot quoted (NextSmartShip + China Fulfillment)"],
           "P0", "2026-10-31", [
               ([0], "JLC: API app + prototype order",
                "application submitted, order placed",
                "confirmation emails + receipts"),
               ([1], "Warehouse: pilot quote requests sent",
                "both warehouses quoted the 4-supplier pilot",
                "sent emails + receipts"),
           ])
    return ids


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed-q4", action="store_true")
    ap.add_argument("--list", nargs="?", const="", default=None)
    ap.add_argument("--show", type=int, default=None)
    ap.add_argument("--done", nargs=2, metavar=("TASK", "RECEIPT"), default=None)
    args = ap.parse_args()
    if args.seed_q4:
        print("seeded goals:", seed_q4())
    if args.list is not None:
        for g in list_goals(args.list or None):
            print(f"{g['id']} [{g['priority']}] {g['entity']:20} {g['title'][:45]:45} "
                  f"{g['derived']:5} {g['covered']} {g['by_status']}")
    if args.show:
        import json as _j
        print(_j.dumps(goal_status(args.show), indent=1)[:2500])
    if args.done:
        set_task_status(int(args.done[0]), "DONE", receipt_id=args.done[1])
        print("ok")
