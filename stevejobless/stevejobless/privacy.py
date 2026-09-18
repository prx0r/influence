"""Privacy — PII redaction + retention sweeper (GDPR story for customer data).

Pattern credit: sara's PII anonymizer + AIReceptionist's retention sweeper
(both AGPL — cleanroom reimplementation, no pasted code).
Rule: transcripts are operational data with a TTL, not an archive.
"""
from __future__ import annotations

import json
import re
from datetime import timedelta

PHONE_RE = re.compile(r"\+?\d[\d\s().-]{7,}\d")
EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
POSTCODE_RE = re.compile(r"\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b", re.IGNORECASE)


def redact(text: str) -> str:
    """Redact phones, emails, postcodes. Applied to logs/exports, never to
    the live job record the tradie needs to do the work."""
    text = EMAIL_RE.sub("[email]", text)
    text = POSTCODE_RE.sub("[postcode]", text)
    return PHONE_RE.sub("[phone]", text)


def retention_sweep(db, days: int = 90) -> dict:
    """Delete JobMessages older than `days` (transcripts have a TTL; job
    metadata, quotes and stats are kept). Returns counts per job."""
    from .tradie import JobMessage, utcnow

    from sqlalchemy import select

    cutoff = utcnow() - timedelta(days=days)
    old = db.scalars(select(JobMessage).where(JobMessage.created_at < cutoff)).all()
    per_job: dict[int, int] = {}
    for m in old:
        per_job[m.job_id] = per_job.get(m.job_id, 0) + 1
        db.delete(m)
    db.commit()
    return {"deleted": len(old), "jobs_touched": len(per_job), "retention_days": days}
