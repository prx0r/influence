"""Campaigns — group packs → channels → track. Stdlib sqlite3 only.

A campaign is: occasion + packs + channels + budget + window.
Items track each pack×channel with status + receipts. Links to actions.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("DASH_DB", os.path.join(_HERE, "..", "dash", "influence.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS campaigns (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  brand_slug TEXT DEFAULT 'oddhobb',
  occasion TEXT DEFAULT 'generic',
  status TEXT DEFAULT 'draft',
  budget_usd REAL DEFAULT 0,
  spent_usd REAL DEFAULT 0,
  starts_at TEXT,
  ends_at TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS campaign_items (
  id INTEGER PRIMARY KEY,
  campaign_id INTEGER,
  sku TEXT NOT NULL,
  channel TEXT NOT NULL,
  status TEXT DEFAULT 'draft',
  payload_json TEXT DEFAULT '{}',
  external_id TEXT,
  published_at TEXT,
  receipt_id TEXT,
  UNIQUE(campaign_id, sku, channel),
  FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
);
CREATE INDEX IF NOT EXISTS idx_camp_items ON campaign_items(campaign_id, status);
"""


def _db(path: str = DB_PATH):
    db = sqlite3.connect(path, timeout=30)
    db.executescript(SCHEMA)
    return db


def create(name: str, brand_slug: str = "oddhobb", occasion: str = "generic",
           budget_usd: float = 0.0, starts_at: str | None = None,
           ends_at: str | None = None, db_path: str = DB_PATH) -> int:
    db = _db(db_path)
    try:
        cur = db.execute(
            "INSERT INTO campaigns (name,brand_slug,occasion,budget_usd,starts_at,ends_at)"
            " VALUES (?,?,?,?,?,?)",
            (name, brand_slug, occasion, budget_usd, starts_at, ends_at))
        db.commit()
        return cur.lastrowid
    finally:
        db.close()


def add_item(campaign_id: int, sku: str, channel: str,
             payload: dict | None = None, db_path: str = DB_PATH) -> int:
    db = _db(db_path)
    try:
        cur = db.execute(
            "INSERT OR IGNORE INTO campaign_items (campaign_id,sku,channel,payload_json)"
            " VALUES (?,?,?,?)",
            (campaign_id, sku, channel, json.dumps(payload or {})))
        db.commit()
        row = db.execute("SELECT id FROM campaign_items WHERE campaign_id=? AND sku=? AND channel=?",
                         (campaign_id, sku, channel)).fetchone()
        return row[0] if row else cur.lastrowid
    finally:
        db.close()


def set_item_status(item_id: int, status: str, external_id: str | None = None,
                    receipt_id: str | None = None, db_path: str = DB_PATH) -> None:
    assert status in ("draft", "queued", "published", "failed")
    db = _db(db_path)
    try:
        if status == "published":
            db.execute("UPDATE campaign_items SET status=?,external_id=?,receipt_id=?,"
                       " published_at=datetime('now') WHERE id=?",
                       (status, external_id, receipt_id, item_id))
        else:
            db.execute("UPDATE campaign_items SET status=? WHERE id=?", (status, item_id))
        db.commit()
    finally:
        db.close()


def add_spend(campaign_id: int, amount_usd: float, db_path: str = DB_PATH) -> dict:
    """Add spend. Returns {ok, spent, cap, remaining}. Fail closed on cap."""
    db = _db(db_path)
    try:
        row = db.execute("SELECT budget_usd,spent_usd FROM campaigns WHERE id=?",
                         (campaign_id,)).fetchone()
        if not row:
            return {"ok": False, "reason": "no such campaign"}
        cap, spent = row
        if cap and (spent + amount_usd) > cap:
            return {"ok": False, "reason": f"cap ${cap:.2f} exceeded",
                    "spent": spent, "cap": cap}
        db.execute("UPDATE campaigns SET spent_usd=spent_usd+? WHERE id=?",
                   (amount_usd, campaign_id))
        db.commit()
        return {"ok": True, "spent": round(spent + amount_usd, 4), "cap": cap,
                "remaining": round((cap - spent - amount_usd) if cap else -1, 4)}
    finally:
        db.close()


def get_campaign(campaign_id: int, db_path: str = DB_PATH) -> dict | None:
    db = _db(db_path)
    try:
        c = db.execute("SELECT id,name,brand_slug,occasion,status,budget_usd,spent_usd,"
                       " starts_at,ends_at,created_at FROM campaigns WHERE id=?",
                       (campaign_id,)).fetchone()
        if not c:
            return None
        items = [{
            "id": r[0], "sku": r[1], "channel": r[2], "status": r[3],
            "external_id": r[4], "published_at": r[5], "receipt_id": r[6],
        } for r in db.execute(
            "SELECT id,sku,channel,status,external_id,published_at,receipt_id"
            " FROM campaign_items WHERE campaign_id=? ORDER BY channel,sku",
            (campaign_id,)).fetchall()]
        # join with actions for cost
        cost = db.execute(
            "SELECT COALESCE(SUM(cost_usd),0) FROM actions WHERE campaign IN"
            " (SELECT name FROM campaigns WHERE id=?)", (campaign_id,)).fetchone()[0]
        return {
            "id": c[0], "name": c[1], "brand": c[2], "occasion": c[3],
            "status": c[4], "budget_usd": c[5], "spent_usd": c[6],
            "starts_at": c[7], "ends_at": c[8], "created_at": c[9],
            "items": items,
            "item_counts": {s: sum(1 for i in items if i["status"] == s)
                            for s in ("draft", "queued", "published", "failed")},
            "logged_spend_usd": round(cost or 0, 4),
        }
    finally:
        db.close()


def list_campaigns(brand_slug: str | None = None, db_path: str = DB_PATH) -> list[dict]:
    db = _db(db_path)
    try:
        q = "SELECT id,name,brand_slug,occasion,status,budget_usd,spent_usd FROM campaigns"
        args: list = []
        if brand_slug:
            q += " WHERE brand_slug=?"; args.append(brand_slug)
        q += " ORDER BY id DESC"
        out = []
        for r in db.execute(q, args).fetchall():
            n = db.execute("SELECT COUNT(*), SUM(status='published') FROM campaign_items"
                           " WHERE campaign_id=?", (r[0],)).fetchone()
            out.append({"id": r[0], "name": r[1], "brand": r[2], "occasion": r[3],
                        "status": r[4], "budget_usd": r[5], "spent_usd": r[6],
                        "items": n[0], "published": n[1] or 0})
        return out
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--create", nargs="+", help="NAME [brand] [occasion] [budget]")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--show", type=int, default=None)
    ap.add_argument("--add-item", nargs=3, metavar=("CAMP", "SKU", "CHANNEL"), default=None)
    args = ap.parse_args()
    if args.create:
        name = args.create[0]
        brand = args.create[1] if len(args.create) > 1 else "oddhobb"
        occ = args.create[2] if len(args.create) > 2 else "generic"
        budget = float(args.create[3]) if len(args.create) > 3 else 0.0
        print("campaign", create(name, brand, occ, budget))
    if args.list:
        for c in list_campaigns():
            print(f"{c['id']} {c['name']:30} {c['occasion']:12} {c['status']:10} ${c['spent_usd']:.2f}/${c['budget_usd']:.2f} items={c['items']} pub={c['published']}")
    if args.show:
        print(json.dumps(get_campaign(args.show), indent=1)[:2000])
    if args.add_item:
        print("item", add_item(int(args.add_item[0]), args.add_item[1], args.add_item[2]))
