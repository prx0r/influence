"""Accountless sessions + XMR invoice lifecycle + exactly-once capability mint.
No name, email, phone, or account anywhere. Amounts are integers (atomic
units), never floats. A callback is a wake-up signal, never truth: only an
explicit observation with confirmations moves an invoice. Each invoice mints
at most once (unique constraint); the bearer token is shown once and only
its hash persists."""
from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
import time

SESSIONS = os.getenv("SESSION_DB", os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "dash", "sessions.db"))

INVOICE_STATES = ("PENDING", "PARTIAL", "CONFIRMED", "EXPIRED")


def _hash(token: str) -> str:
    return "sha256:" + hashlib.sha256(token.encode()).hexdigest()


class SessionStore:
    def __init__(self, path: str = SESSIONS):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.execute("""CREATE TABLE IF NOT EXISTS sessions
            (id TEXT PRIMARY KEY, cap_hash TEXT, state TEXT, created_at INTEGER)""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS invoices
            (id TEXT PRIMARY KEY, session_id TEXT, subaddress TEXT,
             expected INTEGER, min_conf INTEGER, state TEXT,
             observed INTEGER, expires_at INTEGER)""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS capabilities
            (id TEXT PRIMARY KEY, invoice_id TEXT UNIQUE, session_id TEXT,
             cap_hash TEXT, issued_at INTEGER)""")
        self.db.commit()

    def create_session(self) -> dict:
        sid = "sess-" + secrets.token_hex(12)
        token = secrets.token_hex(32)
        now = int(time.time())
        self.db.execute("INSERT INTO sessions VALUES (?,?,?,?)",
                        (sid, _hash(token), "UNFUNDED", now))
        self.db.commit()
        return {"session_id": sid, "capability_token": token, "state": "UNFUNDED"}

    def create_invoice(self, session_id: str, expected_atomic: int, subaddress: str,
                       min_conf: int = 10, ttl_s: int = 3600) -> dict:
        if expected_atomic <= 0:
            raise ValueError("expected must be positive atomic units")
        if not self.db.execute("SELECT 1 FROM sessions WHERE id=?", (session_id,)).fetchone():
            raise KeyError(f"unknown session {session_id}")
        iid = "inv-" + secrets.token_hex(12)
        now = int(time.time())
        self.db.execute("INSERT INTO invoices VALUES (?,?,?,?,?,?,?,?)",
                        (iid, session_id, subaddress, expected_atomic, min_conf,
                         "PENDING", 0, now + ttl_s))
        self.db.commit()
        return {"invoice_id": iid, "state": "PENDING", "expected_atomic": expected_atomic}

    def observe_payment(self, invoice_id: str, observed_atomic: int,
                        confirmations: int) -> str:
        """Record a payment observation. Under-confirmation waits; underpayment
        waits as PARTIAL; expiry wins over everything except CONFIRMED."""
        row = self.db.execute(
            "SELECT state, expected, min_conf, expires_at FROM invoices WHERE id=?",
            (invoice_id,)).fetchone()
        if not row:
            raise KeyError(f"unknown invoice {invoice_id}")
        state, expected, min_conf, expires_at = row
        now = int(time.time())
        if state == "CONFIRMED":
            return "CONFIRMED"
        if now > expires_at:
            self.db.execute("UPDATE invoices SET state=? WHERE id=?", ("EXPIRED", invoice_id))
            self.db.commit()
            return "EXPIRED"
        if observed_atomic < expected or confirmations < min_conf:
            new = "PARTIAL"
        else:
            new = "CONFIRMED"
        self.db.execute("UPDATE invoices SET state=?, observed=? WHERE id=?",
                        (new, observed_atomic, invoice_id))
        self.db.commit()
        if new == "CONFIRMED":
            self.db.execute("UPDATE sessions SET state=? WHERE id=(SELECT session_id FROM invoices WHERE id=?)",
                            ("FUNDED", invoice_id))
            self.db.commit()
        return new

    def mint_capability(self, invoice_id: str) -> dict:
        """Exactly-once mint per invoice. Token returned once; hash persisted."""
        row = self.db.execute(
            "SELECT state, session_id FROM invoices WHERE id=?", (invoice_id,)).fetchone()
        if not row or row[0] != "CONFIRMED":
            raise ValueError("invoice not CONFIRMED")
        token = secrets.token_hex(32)
        cid = "cap-" + secrets.token_hex(8)
        try:
            self.db.execute("INSERT INTO capabilities VALUES (?,?,?,?,?)",
                            (cid, invoice_id, row[1], _hash(token), int(time.time())))
            self.db.commit()
        except sqlite3.IntegrityError:
            raise ValueError("invoice already minted (no double credit)")
        return {"capability_id": cid, "capability_token": token, "session_id": row[1]}

    def check_capability(self, capability_id: str, token: str) -> bool:
        row = self.db.execute("SELECT cap_hash FROM capabilities WHERE id=?",
                              (capability_id,)).fetchone()
        if not row:
            return False
        return secrets.compare_digest(row[0], _hash(token))
