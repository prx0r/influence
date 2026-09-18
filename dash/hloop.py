"""HLoop minimal: prediction banked at display, required before decide. Ported from qpfinal human/hloop patterns.
No ML yet: prediction records task payload hash + display time. Scoring and autonomy ladders arrive later;
the invariant that matters now — no answer without a prior banked prediction — is enforced."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time


class HLoop:
    def __init__(self, path: str):
        self.db = sqlite3.connect(path)
        self.db.execute("""CREATE TABLE IF NOT EXISTS predictions
            (ref TEXT PRIMARY KEY, task_id TEXT, payload_hash TEXT, at INTEGER, used INTEGER DEFAULT 0)""")
        for col in ("family TEXT DEFAULT 'general'", "pred_p REAL", "outcome INTEGER"):
            try:
                self.db.execute(f"ALTER TABLE predictions ADD COLUMN {col}")
            except sqlite3.OperationalError:
                pass  # already migrated
        self.db.commit()

    def present(self, task: dict, family: str = "general", pred_p: float | None = None) -> str:
        if pred_p is not None and not 0.0 <= pred_p <= 1.0:
            raise ValueError("pred_p must be in [0,1]")
        payload = {k: task.get(k) for k in ("id", "influencer", "resource_key", "title", "instructions", "options")}
        ph = "sha256:" + hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        ref = "pred-" + hashlib.sha256(f"{task['id']}:{time.time_ns()}".encode()).hexdigest()[:16]
        self.db.execute("INSERT INTO predictions VALUES (?,?,?,?,0,?,?,NULL)",
                        (ref, task["id"], ph, int(time.time()), family, pred_p))
        self.db.commit()
        return ref

    def decide(self, task_id: str, prediction_ref: str, outcome: int | None = None) -> None:
        row = self.db.execute("SELECT task_id, used FROM predictions WHERE ref=?", (prediction_ref,)).fetchone()
        if not row:
            raise KeyError("no such prediction — present the task first")
        if row[0] != task_id:
            raise ValueError("prediction-task mismatch")
        if row[1]:
            raise ValueError("prediction already used")
        if outcome is not None and outcome not in (0, 1):
            raise ValueError("outcome must be 0/1")
        self.db.execute("UPDATE predictions SET used=1, outcome=? WHERE ref=?",
                        (outcome, prediction_ref))
        self.db.commit()

    def calibration(self) -> dict:
        import sys as _sys
        import os as _os
        if _os.path.dirname(_os.path.dirname(__file__)) not in _sys.path:
            _sys.path.insert(0, _os.path.dirname(_os.path.dirname(__file__)))
        from qp.calibration import CalibrationLog
        rows = self.db.execute(
            "SELECT ref, family, pred_p FROM predictions WHERE pred_p IS NOT NULL").fetchall()
        outs = {r[0]: r[1] for r in
                self.db.execute("SELECT ref, outcome FROM predictions WHERE outcome IS NOT NULL").fetchall()}
        log = CalibrationLog(self.db)
        for ref, fam, p in rows:
            log.log_prediction(ref, fam or "general", p)
            if ref in outs:
                log.log_outcome(ref, outs[ref])
        return log.report()
