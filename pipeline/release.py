"""ChannelRelease — immutable derived channel object.

Pack revision → compiler → ChannelRelease → review → publish.

A release pins: pack hash, compiler version, exact payload, exact media,
exact price source, payload hash. Humans approve the hash. Grants authorize
the hash. Executors check the hash. Any changed byte → re-review.

Price ALWAYS resolves from catalog pricing truth. Influence never invents
or drifts price. (dir 7)
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
try:
    from catalog import load as catalog_load, pack_hash, level, may
except ImportError:
    from pipeline.catalog import load as catalog_load, pack_hash, level, may  # noqa

DB_PATH = os.getenv("DASH_DB", os.path.join(_HERE, "..", "dash", "influence.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS channel_releases (
  id TEXT PRIMARY KEY,
  brand TEXT NOT NULL,
  channel TEXT NOT NULL,
  sku TEXT NOT NULL,
  pack_hash TEXT NOT NULL,
  compiler TEXT NOT NULL,
  compiler_version TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  payload_hash TEXT NOT NULL,
  media_json TEXT DEFAULT '[]',
  price_source TEXT DEFAULT '',
  price_amount REAL,
  price_currency TEXT DEFAULT 'USD',
  state TEXT DEFAULT 'draft',
  external_id TEXT,
  receipt_id TEXT,
  campaign TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_releases_sku ON channel_releases(sku, channel);
"""

# Channel → minimum pack level required to publish (dir 29)
CHANNEL_MIN_LEVEL = {
    "etsy": "LISTABLE",
    "shopify": "LISTABLE",
    "pinterest": "LISTABLE",
    "x": "LISTABLE",
    "instagram": "LISTABLE",
    "tiktok": "LISTABLE",
    "youtube": "LISTABLE",
    "ads": "PROVEN",
    "bundle": "PROVEN",
    "scale": "PROVEN",
}
_LEVEL_RANK = {"DRAFT": 0, "PRINT_READY": 1, "LISTABLE": 2, "PROVEN": 3, "RETIRED": -1}


def _db(path: str = DB_PATH):
    db = sqlite3.connect(path, timeout=30)
    db.executescript(SCHEMA)
    return db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha(obj) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def _new_id(brand: str, channel: str, sku: str) -> str:
    import time
    raw = f"{brand}:{channel}:{sku}:{time.time_ns()}"
    return f"rel_{hashlib.sha256(raw.encode()).hexdigest()[:12]}"


def resolve_price(sku: str) -> dict:
    """Price from catalog pricing truth. Never invent, never drift. (dir 7)"""
    p = catalog_load(sku)
    listing = p.get("listing") or {}
    price = listing.get("price") or {}
    amount = price.get("amount")
    if amount in (None, 0):
        return {"ok": False,
                "reason": f"{sku}: no approved price in catalog (pricing policy required)",
                "amount": None, "currency": price.get("currency", "USD"),
                "source": "catalog:missing"}
    cost = p.get("cost") or {}
    return {"ok": True, "amount": amount,
            "currency": price.get("currency", "USD"),
            "source": f"catalog:{sku}:listing.price",
            "cost_print": (cost.get("print") or {}).get("amount"),
            "cost_shipping": (cost.get("shipping") or {}).get("amount")}


def create(brand: str, channel: str, sku: str, payload: dict,
           media: list | None = None, campaign: str | None = None,
           compiler: str = "etsy-v1", compiler_version: str = "1",
           db_path: str = DB_PATH) -> dict:
    """Compile a release. Enforces: pack level permission + price truth."""
    # 1. pack level gate (dir 29)
    lv = level(sku)
    need = CHANNEL_MIN_LEVEL.get(channel, "LISTABLE")
    if _LEVEL_RANK.get(lv, 0) < _LEVEL_RANK.get(need, 2) or lv == "RETIRED":
        raise ValueError(f"{sku} is {lv}: {channel} requires {need}")
    # 2. price truth (dir 7)
    pr = resolve_price(sku)
    if not pr["ok"]:
        raise ValueError(pr["reason"])
    # 3. freeze
    ph = pack_hash(sku)
    payload_hash = _sha(payload)
    rid = _new_id(brand, channel, sku)
    db = _db(db_path)
    try:
        db.execute(
            "INSERT INTO channel_releases (id,brand,channel,sku,pack_hash,compiler,"
            " compiler_version,payload_json,payload_hash,media_json,price_source,"
            " price_amount,price_currency,state,campaign)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?, 'draft',?)",
            (rid, brand, channel, sku, ph, compiler, compiler_version,
             json.dumps(payload, sort_keys=True), payload_hash,
             json.dumps(media or []), pr["source"], pr["amount"], pr["currency"],
             campaign))
        db.commit()
    finally:
        db.close()
    return get(rid, db_path)


def get(release_id: str, db_path: str = DB_PATH) -> dict | None:
    db = _db(db_path)
    try:
        r = db.execute("SELECT id,brand,channel,sku,pack_hash,compiler,compiler_version,"
                       " payload_json,payload_hash,media_json,price_source,price_amount,"
                       " price_currency,state,external_id,receipt_id,campaign,created_at"
                       " FROM channel_releases WHERE id=?", (release_id,)).fetchone()
        if not r:
            return None
        return {
            "id": r[0], "brand": r[1], "channel": r[2], "sku": r[3],
            "pack_hash": r[4][:16] if r[4] else "", "compiler": f"{r[5]}@{r[6]}",
            "payload": json.loads(r[7]), "payload_hash": r[8][:16] if r[8] else "",
            "media": json.loads(r[9] or "[]"),
            "price": {"amount": r[11], "currency": r[12], "source": r[10]},
            "state": r[13], "external_id": r[14], "receipt_id": r[15],
            "campaign": r[16], "created_at": r[17],
        }
    finally:
        db.close()


def set_state(release_id: str, state: str, external_id: str | None = None,
              receipt_id: str | None = None, db_path: str = DB_PATH) -> None:
    assert state in ("draft", "review_ready", "approved", "granted", "executing",
                     "verifying", "proven_true", "proven_false", "unknown_reconcile",
                     "rejected")
    db = _db(db_path)
    try:
        if external_id is not None or receipt_id is not None:
            db.execute("UPDATE channel_releases SET state=?,external_id=COALESCE(?,external_id),"
                       " receipt_id=COALESCE(?,receipt_id),updated_at=datetime('now') WHERE id=?",
                       (state, external_id, receipt_id, release_id))
        else:
            db.execute("UPDATE channel_releases SET state=?,updated_at=datetime('now') WHERE id=?",
                       (state, release_id))
        db.commit()
    finally:
        db.close()


def verify_hash(release_id: str, payload: dict, db_path: str = DB_PATH) -> bool:
    """Executor check: current payload hash == granted hash. Any drift → False."""
    db = _db(db_path)
    try:
        row = db.execute("SELECT payload_hash FROM channel_releases WHERE id=?",
                         (release_id,)).fetchone()
        if not row:
            return False
        return row[0] == _sha(payload)
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--price", default=None, metavar="SKU")
    ap.add_argument("--level", default=None, metavar="SKU")
    args = ap.parse_args()
    if args.price:
        print(json.dumps(resolve_price(args.price), indent=1))
    if args.level:
        print(args.level, level(args.level), "listing:" , may(args.level, "listing"))
