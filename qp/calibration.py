"""Calibration: Brier score + ECE per decision family over banked predictions.
Predictions carry a probability; outcomes arrive at decide time. No
probability, no calibration — unjudged rows are counted as support gaps,
never as skill."""
from __future__ import annotations

import sqlite3


def brier(pairs: list[tuple[float, int]]) -> float | None:
    """Mean (p - outcome)^2. None on empty."""
    if not pairs:
        return None
    return round(sum((p - o) ** 2 for p, o in pairs) / len(pairs), 4)


def ece(pairs: list[tuple[float, int]], bins: int = 5) -> float | None:
    """Expected calibration error: |accuracy - confidence| per bin, weighted."""
    if not pairs:
        return None
    buckets: list[list[tuple[float, int]]] = [[] for _ in range(bins)]
    for p, o in pairs:
        i = min(bins - 1, int(p * bins))
        buckets[i].append((p, o))
    n = len(pairs)
    err = 0.0
    for b in buckets:
        if not b:
            continue
        acc = sum(o for _, o in b) / len(b)
        conf = sum(p for p, _ in b) / len(b)
        err += len(b) / n * abs(acc - conf)
    return round(err, 4)


class CalibrationLog:
    """SQLite-backed (pred_ref, family, p, outcome). Outcome NULL = pending."""

    def __init__(self, db: sqlite3.Connection):
        self.db = db
        self.db.execute("""CREATE TABLE IF NOT EXISTS calibration
            (ref TEXT PRIMARY KEY, family TEXT, p REAL, outcome INTEGER)""")
        self.db.commit()

    def log_prediction(self, ref: str, family: str, p: float | None) -> None:
        if p is not None and not 0.0 <= p <= 1.0:
            raise ValueError("p must be in [0,1]")
        self.db.execute("INSERT OR IGNORE INTO calibration VALUES (?,?,?,NULL)",
                        (ref, family, p))
        self.db.commit()

    def log_outcome(self, ref: str, outcome: int) -> None:
        if outcome not in (0, 1):
            raise ValueError("outcome must be 0/1")
        self.db.execute("UPDATE calibration SET outcome=? WHERE ref=?", (outcome, ref))
        self.db.commit()

    def report(self) -> dict:
        rows = self.db.execute(
            "SELECT family, p, outcome FROM calibration WHERE p IS NOT NULL AND outcome IS NOT NULL"
        ).fetchall()
        pending = self.db.execute(
            "SELECT COUNT(*) FROM calibration WHERE outcome IS NULL").fetchone()[0]
        fams: dict[str, list[tuple[float, int]]] = {}
        for fam, p, o in rows:
            fams.setdefault(fam, []).append((p, o))
        return {"families": {f: {"n": len(v), "brier": brier(v), "ece": ece(v)}
                             for f, v in fams.items()},
                "pending": pending, "scored": len(rows)}
