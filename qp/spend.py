"""Spend ledger: the money-proof family in code. propose() checks the budget
cap before anything exists; authorize() binds a validated grant (single-use
counted durably); settle() compares provider readback against the authorized
amount with 10% drift tolerance — drift opens a flag, never a silent edit.
Attempt evidence never settles: settle() requires an explicit readback."""
from __future__ import annotations

import os
import sqlite3
import sys
import time

from qp.authority import Grant, payload_hash, validate

LEDGER = os.getenv("SPEND_LEDGER", os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "dash", "spend.db"))
DRIFT_TOLERANCE = 0.10


class SpendLedger:
    def __init__(self, path: str = LEDGER):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.execute("""CREATE TABLE IF NOT EXISTS spends
            (idem TEXT PRIMARY KEY, purpose TEXT, amount INTEGER, cap INTEGER,
             state TEXT, grant_sig TEXT, uses INTEGER, readback INTEGER,
             updated_at INTEGER)""")
        self.db.commit()

    def propose(self, idem: str, purpose: str, amount: int, cap: int) -> str:
        """Idempotent propose. Over-cap intents are refused, never trimmed."""
        row = self.db.execute("SELECT state FROM spends WHERE idem=?", (idem,)).fetchone()
        if row:
            return row[0]
        if amount <= 0:
            raise ValueError("amount must be positive (minor units)")
        if amount > cap:
            raise ValueError(f"over cap: {amount} > {cap}")
        now = int(time.time())
        self.db.execute("INSERT INTO spends VALUES (?,?,?,?,?,?,?,?,?)",
                        (idem, purpose, amount, cap, "PROPOSED", "", 0, -1, now))
        self.db.commit()
        return "PROPOSED"

    def authorize(self, idem: str, grant: Grant, payload: dict, verify) -> str:
        """Bind a validated grant. Replays and mismatches fail closed."""
        row = self.db.execute("SELECT state, amount, uses FROM spends WHERE idem=?",
                              (idem,)).fetchone()
        if not row:
            raise KeyError(f"unknown spend {idem}")
        state, amount, uses = row
        if state != "PROPOSED":
            raise ValueError(f"spend is {state}, not PROPOSED")
        if payload.get("amount") != amount or payload.get("idem") != idem:
            raise ValueError("payload mismatch (amount/idem must match proposal)")
        ok, reason = validate(grant, "spend.authorize", payload, verify, uses)
        if not ok:
            raise ValueError(f"grant rejected: {reason}")
        now = int(time.time())
        self.db.execute("UPDATE spends SET state=?, grant_sig=?, uses=?, updated_at=? WHERE idem=?",
                        ("AUTHORIZED", grant.signature, uses + 1, now, idem))
        self.db.commit()
        return "AUTHORIZED"

    def settle(self, idem: str, readback_amount: int) -> str:
        """Settle against provider readback. Drift beyond tolerance flags.
        Every settle emits a receipt: TRUE when settled within tolerance,
        FALSE on drift (decisive contradiction), UNKNOWN never (readback
        present means the claim resolves)."""
        import sys
        row = self.db.execute("SELECT state, amount, purpose FROM spends WHERE idem=?",
                              (idem,)).fetchone()
        if not row:
            raise KeyError(f"unknown spend {idem}")
        state, amount, purpose = row
        if state != "AUTHORIZED":
            raise ValueError(f"spend is {state}, not AUTHORIZED")
        if readback_amount < 0:
            raise ValueError("readback required (attempt is not observation)")
        drift = abs(readback_amount - amount) / amount
        final = "FLAGGED_DRIFT" if drift > DRIFT_TOLERANCE else "SETTLED"
        now = int(time.time())
        self.db.execute("UPDATE spends SET state=?, readback=?, updated_at=? WHERE idem=?",
                        (final, readback_amount, now, idem))
        self.db.commit()
        self._emit_receipt(idem, purpose, amount, readback_amount, final)
        return final

    def _emit_receipt(self, idem: str, purpose: str, amount: int,
                      readback: int, final: str) -> dict:
        import os
        from datetime import datetime, timezone
        qp = os.getenv("QPRIVATELY_PATH", "/home/ubuntu/qprivately")
        if qp not in sys.path:
            sys.path.insert(0, qp)
        from acom import objects as O
        from acom import receipts as R
        from acom import store as StoreMod
        iso = datetime.now(timezone.utc).isoformat()
        ev = [O.make_evidence("spend.authorized", amount, "minor", iso,
                              {"class": "ledger", "artifact_hash": "sha256:0"}),
              O.make_evidence("spend.readback", readback, "minor", iso,
                              {"class": "provider", "artifact_hash": "sha256:0"})]
        claim = O.make_claim(f"spend {idem} {purpose}",
                             "influence.spend",
                             "TRUE" if final == "SETTLED" else "FALSE")
        run = O.make_run(task_id=claim["id"], worker="spend-ledger")
        st = StoreMod.Store(os.getenv(
            "RECEIPT_LOG", os.path.join(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__))), "dash", "receipts.jsonl")))
        receipt = R.transition(
            {"cursor": st.cursor, "rules_commit": "qprivately",
             "event_root": st.event_root, "state_root": ""},
            {"id": claim["id"], "target": claim["id"], "claim": claim, "grant": None},
            ev, ["evidence-fresh-v1", "no-duplicate-v1", "claim-resolved-v1"],
            run, proof_level=9)
        st.append("transition", {"receipt": receipt, "evidence": ev, "claim": claim,
                                 "spend": idem})
        return receipt

    def state(self, idem: str) -> str | None:
        row = self.db.execute("SELECT state FROM spends WHERE idem=?", (idem,)).fetchone()
        return row[0] if row else None
