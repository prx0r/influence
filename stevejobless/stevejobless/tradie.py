"""Tradie stack — the business brain for agent-run trade businesses.

Voice agent (Qwen-Omni side) owns real-time conversation. This module owns
everything around it: the tradie kernel (preferences, price book, policies),
the job pipeline (lead → qualified → quoted → scheduled → done → invoiced),
quotes, parts, scheduling options, stats, and job scoring.

Compat: knowledge YAML files here double as voice-agent BUSINESS_CONFIG
(same business/agent/voice/nodes shape, plus a `tradie:` block this side
reads and the voice side ignores).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# Lead lifecycle. `lost` is terminal-but-kept (Rule 10: train on full funnel).
JOB_STATUS = ("new", "qualified", "quoted", "scheduled", "in_progress", "done", "invoiced", "lost")


class TradieKernel(Base):
    """One row per business: the kernel of info the agent has about the tradie."""
    __tablename__ = "tradie_kernels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), unique=True, index=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)  # tradie: block + price_book + prefs
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Job(Base):
    __tablename__ = "tradie_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    customer_name: Mapped[str] = mapped_column(String(180), default="")
    customer_phone: Mapped[str] = mapped_column(String(60), default="")
    customer_address: Mapped[str] = mapped_column(String(300), default="")
    channel: Mapped[str] = mapped_column(String(32), default="voice")  # voice|whatsapp|email|sms|web
    job_type: Mapped[str] = mapped_column(String(120), default="general")
    description: Mapped[str] = mapped_column(Text, default="")
    urgent: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), default="new", index=True)
    quoted_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    final_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_reasons: Mapped[list] = mapped_column(JSON, default=list)
    extra: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class JobMessage(Base):
    """Transcripts + notes on a job. Immutable facts (Rule 5)."""
    __tablename__ = "tradie_job_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("tradie_jobs.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(32))  # customer|agent|tradie|system
    channel: Mapped[str] = mapped_column(String(32), default="voice")
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Quote(Base):
    """Drafted quotes. Drafts only — sending needs explicit tradie confirm."""
    __tablename__ = "tradie_quotes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("tradie_jobs.id", ondelete="CASCADE"), index=True)
    line_items: Mapped[list] = mapped_column(JSON, default=list)
    total: Mapped[float] = mapped_column(Float, default=0.0)
    message: Mapped[str] = mapped_column(Text, default="")  # customer-facing draft
    status: Mapped[str] = mapped_column(String(32), default="draft")  # draft|approved|sent|accepted|rejected
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Invoice(Base):
    """Invoices grow from accepted work. CSV export feeds the accountant (tax stepping stone)."""
    __tablename__ = "tradie_invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("tradie_jobs.id", ondelete="CASCADE"), index=True)
    number: Mapped[str] = mapped_column(String(32), unique=True)
    line_items: Mapped[list] = mapped_column(JSON, default=list)
    total: Mapped[float] = mapped_column(Float, default=0.0)  # ex-VAT
    vat_rate: Mapped[float] = mapped_column(Float, default=0.2)
    vat_amount: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(32), default="draft")  # draft|sent|paid|overdue
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


def migrate(engine) -> None:
    """Additive-only migrations for live DBs (create_all covers new tables,
    not new columns). Idempotent via PRAGMA inspection."""
    from sqlalchemy import text

    with engine.begin() as conn:
        cols = {r[1] for r in conn.execute(text("PRAGMA table_info(tradie_invoices)")).all()}
        for name, ddl in (("vat_rate", "FLOAT DEFAULT 0.2"), ("vat_amount", "FLOAT DEFAULT 0.0")):
            if cols and name not in cols:
                conn.execute(text(f"ALTER TABLE tradie_invoices ADD COLUMN {name} {ddl}"))


# ---- pure logic: quote builder, scorer, stats (Rule 3: no I/O here) ----

def build_quote(kernel_cfg: dict[str, Any], job: dict[str, Any],
                parts_prices: dict[str, float] | None = None) -> dict[str, Any]:
    """Price-book quote. Never invents: unknown job_type → range + human review flag.
    parts_prices optionally fills estimates with live/fallback supplier prices."""
    book = (kernel_cfg.get("price_book") or {})
    entry = book.get(job.get("job_type", ""), {})
    items: list[dict[str, Any]] = []
    needs_review = False
    if entry:
        labour = float(entry.get("labour", 0))
        items.append({"label": f"Labour — {job.get('job_type')}", "amount": labour})
        for part in entry.get("typical_parts", []):
            if parts_prices and part in parts_prices:
                items.append({"label": f"Parts — {part}", "amount": float(parts_prices[part])})
            else:
                items.append({"label": f"Parts (est.) — {part}", "amount": 0.0, "tbd": True})
        base = labour
    else:
        low, high = (kernel_cfg.get("default_range") or [80, 150])
        items.append({"label": "Site visit + diagnosis", "amount": float(low)})
        base, needs_review = float(low), True
    mult = 1.0
    reasons = []
    if job.get("after_hours"):
        mult *= float(kernel_cfg.get("after_hours_multiplier", 1.5))
        reasons.append("after-hours ×1.5")
    dist = float(job.get("distance_km") or 0)
    callout_per_km = float(kernel_cfg.get("callout_per_km", 0))
    if dist and callout_per_km:
        items.append({"label": f"Callout — {dist:.0f} km", "amount": round(dist * callout_per_km, 2)})
    total = round(base * mult + sum(i.get("amount", 0) for i in items[1:]), 2)
    msg = (
        f"Hi {job.get('customer_name') or 'there'}! For {job.get('job_type','the job')}: "
        f"£{total:.0f}" + (" (estimate — final quote after site visit)" if needs_review or any(i.get("tbd") for i in items) else "")
        + (f" ({'; '.join(reasons)})" if reasons else "")
        + ". Want me to book you in?"
    )
    return {"line_items": items, "total": total, "message": msg, "needs_review": needs_review}


def score_job(kernel_cfg: dict[str, Any], job: dict[str, Any], stats: dict[str, dict] | None = None) -> dict[str, Any]:
    """Worth-doing score 0-100. Same feed, different order per tradie (insta-algo for jobs)."""
    prefs = kernel_cfg.get("preferences") or {}
    score = 50.0
    reasons = []
    aff = (prefs.get("job_affinity") or {}).get(job.get("job_type"), 0)
    score += aff * 10
    if aff:
        reasons.append(f"affinity {aff:+d}")
    dist = float(job.get("distance_km") or 0)
    max_d = float(prefs.get("max_distance_km", 30))
    if dist > max_d:
        score -= 25
        reasons.append(f"{dist:.0f}km > {max_d:.0f}km max")
    elif dist:
        score -= dist * 0.5
        reasons.append(f"{dist:.0f}km away")
    price = float(job.get("quoted_price") or 0)
    if price >= float(prefs.get("min_job_value", 0)):
        score += 10
        reasons.append("above min value")
    if job.get("urgent") and not prefs.get("takes_emergency", True):
        score -= 15
        reasons.append("urgent, tradie avoids emergencies")
    st = (stats or {}).get(job.get("job_type", ""), {})
    if st.get("avg_min") and st["avg_min"] > prefs.get("max_typical_min", 240):
        score -= 10
        reasons.append(f"usually {st['avg_min']:.0f}min — long job")
    if job.get("preferred_slot") == "morning" and "morning" in (prefs.get("preferred_slots") or []):
        score += 5
        reasons.append("morning person ✓")
    score = max(0, min(100, round(score, 1)))
    verdict = "take" if score >= 65 else "maybe" if score >= 40 else "skip"
    return {"score": score, "verdict": verdict, "reasons": reasons}


def job_stats(jobs: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    """Avg duration + revenue by job_type from done/invoiced jobs."""
    acc: dict[str, dict[str, float]] = {}
    for j in jobs:
        if j.get("status") not in ("done", "invoiced"):
            continue
        t = j.get("job_type", "general")
        a = acc.setdefault(t, {"n": 0, "mins": 0.0, "revenue": 0.0})
        a["n"] += 1
        if j.get("duration_min"):
            a["mins"] += j["duration_min"]
        if j.get("final_price") or j.get("quoted_price"):
            a["revenue"] += j.get("final_price") or j.get("quoted_price") or 0
    return {t: {"n": v["n"], "avg_min": round(v["mins"] / v["n"], 1) if v["n"] else 0,
               "avg_revenue": round(v["revenue"] / v["n"], 2) if v["n"] else 0} for t, v in acc.items()}


def calibration(jobs: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    """Rule 9: are our verdicts calibrated? Per score-band: win rate
    (reached done/invoiced vs lost) + avg margin (final/quoted)."""
    bands: dict[str, dict[str, float]] = {}
    for j in jobs:
        if j.get("score") is None or j.get("status") not in ("done", "invoiced", "lost"):
            continue
        s = float(j["score"])
        band = "take(65+)" if s >= 65 else "maybe(40-65)" if s >= 40 else "skip(<40)"
        b = bands.setdefault(band, {"n": 0, "won": 0, "margin_sum": 0.0, "margin_n": 0})
        b["n"] += 1
        if j["status"] in ("done", "invoiced"):
            b["won"] += 1
            if j.get("final_price") and j.get("quoted_price"):
                b["margin_sum"] += j["final_price"] / j["quoted_price"]
                b["margin_n"] += 1
    return {k: {"n": int(v["n"]), "win_rate": round(v["won"] / v["n"], 2) if v["n"] else 0,
               "avg_margin": round(v["margin_sum"] / v["margin_n"], 2) if v["margin_n"] else 0}
            for k, v in bands.items()}
