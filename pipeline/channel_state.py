"""Per-account operator state — the Clipping Bench lesson.

Each social account has its own: posting budget, quality threshold,
cooldown windows, engagement history, performance ledger. Agents propose
freely; the controller decides if publishing is allowed.

See docs/pipeline/FINAL-STACK.md (sleepintel pattern).
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone, timedelta

_HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("DASH_DB", os.path.join(_HERE, "..", "dash", "influence.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS channel_accounts (
  id INTEGER PRIMARY KEY,
  platform TEXT NOT NULL,            -- x | instagram | tiktok | youtube | pinterest
  handle TEXT NOT NULL,              -- @oddhobb
  brand_slug TEXT DEFAULT 'oddhobb', -- oddhobb | pogtown | ...
  status TEXT DEFAULT 'active',      -- active | cooldown | paused | banned
  daily_budget INTEGER DEFAULT 3,    -- max posts per day
  quality_threshold REAL DEFAULT 0.7, -- min score to publish (0-1)
  cooldown_until TEXT,               -- ISO timestamp or NULL
  cooldown_reason TEXT DEFAULT '',
  posts_today INTEGER DEFAULT 0,
  posts_total INTEGER DEFAULT 0,
  last_post_at TEXT,
  avg_engagement REAL DEFAULT 0,     -- rolling average
  total_views INTEGER DEFAULT 0,
  total_clicks INTEGER DEFAULT 0,
  total_orders INTEGER DEFAULT 0,
  notes TEXT DEFAULT '',
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now')),
  UNIQUE(platform, handle)
);
CREATE TABLE IF NOT EXISTS account_events (
  id INTEGER PRIMARY KEY,
  account_id INTEGER,
  at TEXT NOT NULL,
  kind TEXT NOT NULL,                -- post | cooldown_start | cooldown_end | metric | threshold_change
  detail_json TEXT DEFAULT '{}',
  FOREIGN KEY (account_id) REFERENCES channel_accounts(id)
);
CREATE INDEX IF NOT EXISTS idx_acct_events ON account_events(account_id, at);
"""


def _db(path: str = DB_PATH):
    db = sqlite3.connect(path, timeout=30)
    db.executescript(SCHEMA)
    return db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def upsert_account(platform: str, handle: str, brand_slug: str = "oddhobb",
                   daily_budget: int = 3, quality_threshold: float = 0.7,
                   db_path: str = DB_PATH) -> int:
    db = _db(db_path)
    try:
        row = db.execute("SELECT id FROM channel_accounts WHERE platform=? AND handle=?",
                         (platform, handle)).fetchone()
        if row:
            return row[0]
        cur = db.execute(
            "INSERT INTO channel_accounts (platform,handle,brand_slug,daily_budget,quality_threshold)"
            " VALUES (?,?,?,?,?)",
            (platform, handle, brand_slug, daily_budget, quality_threshold))
        db.commit()
        return cur.lastrowid
    finally:
        db.close()


def can_publish(platform: str, handle: str, quality_score: float = 1.0,
                db_path: str = DB_PATH) -> dict:
    """Controller decision: is publishing allowed right now? Returns {ok, reason}."""
    db = _db(db_path)
    try:
        r = db.execute(
            "SELECT id,status,daily_budget,quality_threshold,cooldown_until,"
            " posts_today,last_post_at FROM channel_accounts"
            " WHERE platform=? AND handle=?", (platform, handle)).fetchone()
        if not r:
            return {"ok": False, "reason": "account not registered"}
        aid, status, budget, threshold, cd_until, today, last = r
        if status in ("paused", "banned"):
            return {"ok": False, "reason": f"account {status}"}
        if status == "cooldown" or (cd_until and cd_until > _now()):
            return {"ok": False, "reason": f"cooldown until {cd_until}"}
        # reset daily counter if new day
        today_str = _now()[:10]
        if not last or last[:10] != today_str:
            db.execute("UPDATE channel_accounts SET posts_today=0 WHERE id=?", (aid,))
            db.commit()
            today = 0
        if today >= budget:
            return {"ok": False, "reason": f"daily budget reached ({today}/{budget})"}
        if quality_score < (threshold or 0.7):
            return {"ok": False, "reason": f"quality {quality_score:.2f} below threshold {threshold}"}
        return {"ok": True, "reason": "allowed", "account_id": aid}
    finally:
        db.close()


def record_post(platform: str, handle: str, external_id: str = "",
                db_path: str = DB_PATH) -> None:
    db = _db(db_path)
    try:
        db.execute(
            "UPDATE channel_accounts SET posts_today=posts_today+1, posts_total=posts_total+1,"
            " last_post_at=?, updated_at=datetime('now')"
            " WHERE platform=? AND handle=?", (_now(), platform, handle))
        aid = db.execute("SELECT id FROM channel_accounts WHERE platform=? AND handle=?",
                         (platform, handle)).fetchone()
        if aid:
            db.execute("INSERT INTO account_events (account_id,at,kind,detail_json)"
                       " VALUES (?,?,?,?)",
                       (aid[0], _now(), "post", json.dumps({"external_id": external_id})))
        db.commit()
    finally:
        db.close()


def set_cooldown(platform: str, handle: str, until_hours: int, reason: str,
                 db_path: str = DB_PATH) -> None:
    until = (datetime.now(timezone.utc) + timedelta(hours=until_hours)).isoformat()
    db = _db(db_path)
    try:
        db.execute("UPDATE channel_accounts SET status='cooldown', cooldown_until=?,"
                   " cooldown_reason=?, updated_at=datetime('now')"
                   " WHERE platform=? AND handle=?",
                   (until, reason, platform, handle))
        aid = db.execute("SELECT id FROM channel_accounts WHERE platform=? AND handle=?",
                         (platform, handle)).fetchone()
        if aid:
            db.execute("INSERT INTO account_events (account_id,at,kind,detail_json)"
                       " VALUES (?,?,?,?)",
                       (aid[0], _now(), "cooldown_start",
                        json.dumps({"until": until, "reason": reason})))
        db.commit()
    finally:
        db.close()


def record_metrics(platform: str, handle: str, views: int = 0,
                   clicks: int = 0, orders: int = 0,
                   db_path: str = DB_PATH) -> None:
    """Performance feedback: update rolling totals."""
    db = _db(db_path)
    try:
        db.execute(
            "UPDATE channel_accounts SET total_views=total_views+?,"
            " total_clicks=total_clicks+?, total_orders=total_orders+?,"
            " updated_at=datetime('now') WHERE platform=? AND handle=?",
            (views, clicks, orders, platform, handle))
        aid = db.execute("SELECT id FROM channel_accounts WHERE platform=? AND handle=?",
                         (platform, handle)).fetchone()
        if aid:
            db.execute("INSERT INTO account_events (account_id,at,kind,detail_json)"
                       " VALUES (?,?,?,?)",
                       (aid[0], _now(), "metric",
                        json.dumps({"views": views, "clicks": clicks, "orders": orders})))
        db.commit()
    finally:
        db.close()


def list_accounts(brand_slug: str | None = None, db_path: str = DB_PATH) -> list[dict]:
    db = _db(db_path)
    try:
        q = ("SELECT id,platform,handle,brand_slug,status,daily_budget,quality_threshold,"
             " cooldown_until,posts_today,posts_total,last_post_at,"
             " total_views,total_clicks,total_orders FROM channel_accounts")
        args: list = []
        if brand_slug:
            q += " WHERE brand_slug=?"; args.append(brand_slug)
        q += " ORDER BY platform, handle"
        return [{
            "id": r[0], "platform": r[1], "handle": r[2], "brand": r[3],
            "status": r[4], "budget": f"{r[8]}/{r[5]}", "threshold": r[6],
            "cooldown_until": r[7], "posts_total": r[9], "last_post": r[10],
            "views": r[11], "clicks": r[12], "orders": r[13],
        } for r in db.execute(q, args).fetchall()]
    finally:
        db.close()


def seed_oddhobb(db_path: str = DB_PATH) -> int:
    """Register known oddhobb accounts from bgraph/store.json."""
    accounts = [
        ("x", "@oddhobb", "oddhobb"),
        ("instagram", "@oddhobbstudio", "oddhobb"),
        ("tiktok", "@oddhobb", "oddhobb"),
        ("youtube", "@oddhobbstudio", "oddhobb"),
        ("pinterest", "@oddhobbstudio", "oddhobb"),
    ]
    n = 0
    for platform, handle, brand in accounts:
        db = _db(db_path)
        try:
            if not db.execute("SELECT 1 FROM channel_accounts WHERE platform=? AND handle=?",
                              (platform, handle)).fetchone():
                db.execute(
                    "INSERT INTO channel_accounts (platform,handle,brand_slug) VALUES (?,?,?)",
                    (platform, handle, brand))
                db.commit()
                n += 1
        finally:
            db.close()
    return n


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--check", nargs=3, metavar=("PLATFORM", "HANDLE", "SCORE"),
                    help="check if publishing allowed")
    ap.add_argument("--cooldown", nargs=3, metavar=("PLATFORM", "HANDLE", "HOURS"),
                    help="set cooldown")
    args = ap.parse_args()
    if args.seed:
        print("seeded", seed_oddhobb())
    if args.list:
        for a in list_accounts():
            print(f"{a['platform']:12} {a['handle']:20} {a['status']:10} budget={a['budget']} views={a['views']}")
    if args.check:
        print(can_publish(args.check[0], args.check[1], float(args.check[2])))
    if args.cooldown:
        set_cooldown(args.cooldown[0], args.cooldown[1], int(args.cooldown[2]), "manual")
        print("cooldown set")
