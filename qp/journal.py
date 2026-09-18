"""Effect journal: idempotency-first crash semantics. Persist proposal before acting; reconcile, never blindly retry."""
from __future__ import annotations

import sqlite3
import time

STATES = ("PROPOSED", "AUTHORIZED", "EXECUTING", "PROVEN_TRUE", "PROVEN_FALSE", "UNKNOWN_RECONCILE")

_TERMINAL = {"PROVEN_TRUE", "PROVEN_FALSE"}
_ALLOWED = {
    "PROPOSED": {"AUTHORIZED", "UNKNOWN_RECONCILE"},
    "AUTHORIZED": {"EXECUTING", "UNKNOWN_RECONCILE"},
    "EXECUTING": {"PROVEN_TRUE", "PROVEN_FALSE", "UNKNOWN_RECONCILE"},
    "UNKNOWN_RECONCILE": {"EXECUTING", "PROVEN_TRUE", "PROVEN_FALSE"},
}


class Journal:
    def __init__(self, path: str):
        self.db = sqlite3.connect(path)
        self.db.execute("""CREATE TABLE IF NOT EXISTS effects
            (idem TEXT PRIMARY KEY, action TEXT, state TEXT, grant_ref TEXT, updated_at INTEGER)""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS transitions
            (idem TEXT, frm TEXT, too TEXT, at INTEGER, note TEXT)""")
        self.db.commit()

    def propose(self, idem: str, action: str) -> str:
        """Idempotent: existing key returns current state, never duplicates."""
        row = self.db.execute("SELECT state FROM effects WHERE idem=?", (idem,)).fetchone()
        if row:
            return row[0]
        now = int(time.time())
        self.db.execute("INSERT INTO effects VALUES (?,?,?,?,?)", (idem, action, "PROPOSED", "", now))
        self.db.execute("INSERT INTO transitions VALUES (?,?,?,?,?)", (idem, "", "PROPOSED", now, "propose"))
        self.db.commit()
        return "PROPOSED"

    def transition(self, idem: str, to: str, grant_ref: str = "", note: str = "") -> str:
        row = self.db.execute("SELECT state FROM effects WHERE idem=?", (idem,)).fetchone()
        if not row:
            raise KeyError(f"unknown effect {idem}")
        frm = row[0]
        if frm in _TERMINAL:
            raise ValueError(f"terminal state {frm} is final")
        if to not in _ALLOWED.get(frm, ()):
            raise ValueError(f"illegal transition {frm}->{to}")
        now = int(time.time())
        self.db.execute("UPDATE effects SET state=?, grant_ref=?, updated_at=? WHERE idem=?",
                        (to, grant_ref or "", now, idem))
        self.db.execute("INSERT INTO transitions VALUES (?,?,?,?,?)", (idem, frm, to, now, note))
        self.db.commit()
        return to

    def state(self, idem: str) -> str | None:
        row = self.db.execute("SELECT state FROM effects WHERE idem=?", (idem,)).fetchone()
        return row[0] if row else None
