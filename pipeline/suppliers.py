"""Supplier entities + email threads. Stdlib sqlite3 only.

Suppliers are manufacturing relationships (JLC, Makerfabs, NextSmartShip…).
Every email in/out is logged with timestamps. Agents draft; humans approve sends.
See docs/pipeline/SUPPLIER-ENTITIES.md.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("DASH_DB", os.path.join(_HERE, "..", "dash", "influence.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS suppliers (
  id INTEGER PRIMARY KEY,
  slug TEXT UNIQUE,
  name TEXT,
  role TEXT,
  status TEXT DEFAULT 'prospect',
  website TEXT,
  contacts_json TEXT DEFAULT '[]',
  domains_json TEXT DEFAULT '[]',
  notes TEXT DEFAULT '',
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS supplier_emails (
  id INTEGER PRIMARY KEY,
  supplier_id INTEGER,
  direction TEXT,
  subject TEXT DEFAULT '',
  body_text TEXT DEFAULT '',
  from_addr TEXT DEFAULT '',
  to_addrs TEXT DEFAULT '[]',
  sent_at TEXT,
  message_id TEXT,
  thread_id TEXT,
  status TEXT DEFAULT 'logged',
  receipt_id TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_supp_emails_supplier ON supplier_emails(supplier_id);
CREATE INDEX IF NOT EXISTS idx_supp_emails_thread ON supplier_emails(thread_id);
CREATE INDEX IF NOT EXISTS idx_supp_emails_at ON supplier_emails(sent_at);
"""

SEED = [
    ("jlc", "JLCPCB / JLC3DP", "fabrication", "prospect", "https://jlcpcb.com",
     [{"email": "support@jlcpcb.com", "role": "support/API"}], ["jlcpcb.com", "jlc3dp.com"],
     "3D parts, CNC, PCB, PCBA, live quoting. API approval needs order history."),
    ("makerfabs", "Makerfabs", "integration", "prospect", "https://www.makerfabs.cc",
     [{"email": "service@makerfabs.com", "role": "services"}], ["makerfabs.com", "makerfabs.cc"],
     "Schematic, PCBA, mech, programming, testing, enclosures, packaging."),
    ("nextsmartship", "NextSmartShip", "fulfilment", "prospect", "https://www.nextsmartship.com",
     [{"email": "sales@nextsmartship.com", "role": "sales"}], ["nextsmartship.com"],
     "China warehousing, kitting, branded boxes, Shopify. No standard MOQ. Custom kitting quoted separately."),
    ("china-fulfillment", "China Fulfillment International", "fulfilment", "prospect", "https://www.china-fulfillment.com",
     [{"email": "support@china-fulfillment.com", "role": "support"}], ["china-fulfillment.com"],
     "Shenzhen receiving, inspection, SKU consolidation, gift packaging. $0.99 pick-pack baseline."),
    ("seeed", "Seeed Studio Fusion", "integration", "prospect", "https://www.seeedstudio.com",
     [{"email": "fusion@seeed.io", "role": "fusion"}], ["seeedstudio.com", "seeed.io"],
     "PCBA, Grove, kitting (5+ sets), Reachy Mini industrialisation experience."),
    ("elecrow", "Elecrow", "integration", "contacted", "https://www.elecrow.com",
     [{"email": "service@elecrow.com", "role": "service"}], ["elecrow.com"],
     "Existing relationship. Turnkey PCBA, sourcing, testing, dropshipping. Asked for design list — reframe as modular family."),
    ("onebookprint", "OneBookPrint", "print", "prospect", "https://onebookprint.com",
     [], ["onebookprint.com"],
     "Guangzhou single-copy hardcover/paperback. Confirm Shenzhen delivery + lead time."),
    ("makr3d", "MAKR3D", "fabrication", "active", "https://makr3d.app",
     [], ["makr3d.app"],
     "UK 3D farm, Huddersfield. Primary UK/EU lane. API live."),
    ("printie", "Printie", "fabrication", "active", "",
     [], [],
     "US 3D farm. Manual quote tool, no public API."),
    ("prodigi", "Prodigi", "print", "active", "https://www.prodigi.com",
     [], ["prodigi.com"],
     "Paper POD. Card SKU CLASSIC-GRE-FEDR-7X5-BLA live. Key in StallShark env."),
]


def _db(path: str = DB_PATH):
    db = sqlite3.connect(path, timeout=30)
    db.executescript(SCHEMA)
    return db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def seed(db_path: str = DB_PATH) -> int:
    """Insert seed suppliers (skip existing). Returns count added."""
    db = _db(db_path)
    try:
        n = 0
        for slug, name, role, status, website, contacts, domains, notes in SEED:
            if db.execute("SELECT 1 FROM suppliers WHERE slug=?", (slug,)).fetchone():
                continue
            db.execute(
                "INSERT INTO suppliers (slug,name,role,status,website,contacts_json,domains_json,notes)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (slug, name, role, status, website,
                 json.dumps(contacts), json.dumps(domains), notes))
            n += 1
        db.commit()
        return n
    finally:
        db.close()


def list_suppliers(status: str | None = None, db_path: str = DB_PATH) -> list[dict]:
    db = _db(db_path)
    try:
        q = "SELECT id,slug,name,role,status,website,contacts_json,domains_json,notes,updated_at FROM suppliers"
        args: list = []
        if status:
            q += " WHERE status=?"; args.append(status)
        q += " ORDER BY CASE status WHEN 'active' THEN 0 WHEN 'trial' THEN 1 WHEN 'quoted' THEN 2 WHEN 'contacted' THEN 3 WHEN 'prospect' THEN 4 ELSE 5 END, name"
        out = []
        for r in db.execute(q, args).fetchall():
            # last email
            last = db.execute(
                "SELECT direction,subject,sent_at,created_at FROM supplier_emails"
                " WHERE supplier_id=? ORDER BY COALESCE(sent_at,created_at) DESC LIMIT 1",
                (r[0],)).fetchone()
            n = db.execute("SELECT COUNT(*) FROM supplier_emails WHERE supplier_id=?", (r[0],)).fetchone()[0]
            out.append({
                "id": r[0], "slug": r[1], "name": r[2], "role": r[3], "status": r[4],
                "website": r[5], "contacts": json.loads(r[6] or "[]"),
                "domains": json.loads(r[7] or "[]"), "notes": r[8],
                "updated_at": r[9], "thread_count": n,
                "last": {"direction": last[0], "subject": last[1],
                         "at": last[2] or last[3]} if last else None,
            })
        return out
    finally:
        db.close()


def match_supplier_by_email(addr: str, db_path: str = DB_PATH) -> dict | None:
    """Find supplier whose domain matches an email address."""
    domain = (addr or "").split("@")[-1].lower().strip()
    if not domain or "@" not in addr:
        return None
    db = _db(db_path)
    try:
        for r in db.execute("SELECT id,slug,name,domains_json FROM suppliers").fetchall():
            for d in json.loads(r[3] or "[]"):
                if domain == d.lower() or domain.endswith("." + d.lower()):
                    return {"id": r[0], "slug": r[1], "name": r[2]}
        return None
    finally:
        db.close()


def log_email(supplier_slug: str, direction: str, subject: str = "",
              body: str = "", from_addr: str = "", to_addrs: list | None = None,
              sent_at: str | None = None, message_id: str | None = None,
              thread_id: str | None = None, status: str = "logged",
              receipt_id: str | None = None,
              db_path: str = DB_PATH) -> int:
    db = _db(db_path)
    try:
        row = db.execute("SELECT id FROM suppliers WHERE slug=?", (supplier_slug,)).fetchone()
        if not row:
            raise KeyError(f"unknown supplier {supplier_slug}")
        sid = row[0]
        if not thread_id:
            # reuse latest thread or start new
            t = db.execute(
                "SELECT thread_id FROM supplier_emails WHERE supplier_id=? AND thread_id IS NOT NULL"
                " ORDER BY id DESC LIMIT 1", (sid,)).fetchone()
            thread_id = t[0] if t else f"thread-{supplier_slug}-{db.execute('SELECT COUNT(DISTINCT thread_id) FROM supplier_emails WHERE supplier_id=?', (sid,)).fetchone()[0] + 1}"
        cur = db.execute(
            "INSERT INTO supplier_emails (supplier_id,direction,subject,body_text,from_addr,to_addrs,"
            " sent_at,message_id,thread_id,status,receipt_id)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (sid, direction, subject, body, from_addr, json.dumps(to_addrs or []),
             sent_at or (_now() if direction == "out" else None),
             message_id, thread_id, status, receipt_id))
        db.execute("UPDATE suppliers SET updated_at=datetime('now') WHERE id=?", (sid,))
        db.commit()
        return cur.lastrowid
    finally:
        db.close()


def thread(supplier_slug: str, limit: int = 20, db_path: str = DB_PATH) -> list[dict]:
    db = _db(db_path)
    try:
        row = db.execute("SELECT id FROM suppliers WHERE slug=?", (supplier_slug,)).fetchone()
        if not row:
            raise KeyError(f"unknown supplier {supplier_slug}")
        rows = db.execute(
            "SELECT id,direction,subject,body_text,from_addr,to_addrs,sent_at,message_id,"
            " thread_id,status,receipt_id,created_at FROM supplier_emails"
            " WHERE supplier_id=? ORDER BY COALESCE(sent_at,created_at) DESC LIMIT ?",
            (row[0], limit)).fetchall()
        return [{
            "id": r[0], "direction": r[1], "subject": r[2],
            "body": (r[3] or "")[:2000], "from": r[4], "to": json.loads(r[5] or "[]"),
            "at": r[6] or r[11], "message_id": r[7], "thread_id": r[8],
            "status": r[9], "receipt_id": r[10],
        } for r in rows]
    finally:
        db.close()


def latest(supplier_slug: str, db_path: str = DB_PATH) -> dict | None:
    t = thread(supplier_slug, 1, db_path)
    return t[0] if t else None


def set_status(slug: str, status: str, db_path: str = DB_PATH) -> None:
    assert status in ("prospect", "contacted", "quoted", "trial", "active", "paused", "dropped")
    db = _db(db_path)
    try:
        db.execute("UPDATE suppliers SET status=?,updated_at=datetime('now') WHERE slug=?",
                   (status, slug))
        db.commit()
    finally:
        db.close()


def quiet(days: int = 7, db_path: str = DB_PATH) -> list[dict]:
    """Contacted/trial/quoted suppliers with no email in `days` days (chase list)."""
    db = _db(db_path)
    try:
        out = []
        for r in db.execute(
                "SELECT id,slug,name,status FROM suppliers"
                " WHERE status IN ('contacted','quoted','trial')").fetchall():
            last = db.execute(
                "SELECT MAX(COALESCE(sent_at,created_at)) FROM supplier_emails WHERE supplier_id=?",
                (r[0],)).fetchone()[0]
            if not last:
                out.append({"slug": r[1], "name": r[2], "status": r[3],
                            "last_contact": None, "days_since": None})
                continue
            try:
                dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
                days_since = (datetime.now(timezone.utc) - dt).days
            except Exception:
                continue
            if days_since >= days:
                out.append({"slug": r[1], "name": r[2], "status": r[3],
                            "last_contact": last, "days_since": days_since})
        return sorted(out, key=lambda x: x["days_since"] or 999, reverse=True)
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--thread", default=None)
    ap.add_argument("--latest", default=None)
    ap.add_argument("--quiet", action="store_true", help="chase list")
    ap.add_argument("--status", nargs=2, metavar=("SLUG", "STATUS"), default=None)
    args = ap.parse_args()
    if args.seed:
        print("seeded", seed())
    if args.list:
        for s in list_suppliers():
            last = f"{s['last']['direction']} {s['last']['at'][:10]}" if s["last"] else "—"
            print(f"{s['slug']:18} {s['role']:12} {s['status']:10} msgs={s['thread_count']} last={last}  {s['name']}")
    if args.thread:
        for e in thread(args.thread):
            to = ",".join(e["to"]) if e["to"] else ""
            print(f"[{e['direction']:^4}] {e['at'][:19] if e['at'] else '?':19} {e['subject'][:50]:50} {e['from']} → {to}")
    if args.latest:
        e = latest(args.latest)
        print(json.dumps(e, indent=1)[:1500] if e else "no emails yet")
    if args.quiet:
        for q in quiet():
            print(f"{q['slug']:18} {q['status']:10} last={q['last_contact'] or 'never':25} {q['days_since']}d  → chase")
    if args.status:
        set_status(*args.status)
        print("ok")
