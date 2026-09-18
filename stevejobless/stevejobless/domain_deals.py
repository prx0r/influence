"""Domain deals — prepare→approve→register→wire state machine + receipts.

Port of DomainArena's DecisionState pattern (own lineage: MIT + cleanroom).
Money moves only on APPROVED + fresh recheck + drift guard + budget cap.
Every transition appends to the deal receipt (Rule 6: every action logged).
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


TRANSITIONS = {
    "DRAFT": {"PREPARED", "REJECTED"},
    "PREPARED": {"APPROVED", "REJECTED", "FAILED"},
    "APPROVED": {"REGISTERED", "REJECTED", "FAILED"},
    "REGISTERED": {"WIRED", "FAILED"},
    "WIRED": {"VERIFIED", "FAILED"},
    "VERIFIED": set(),
    "REJECTED": set(),
    "FAILED": {"DRAFT"},
}


class DomainDeal(Base):
    __tablename__ = "domain_deals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    domain: Mapped[str] = mapped_column(String(255), index=True)
    provider: Mapped[str] = mapped_column(String(32))  # porkbun|namecom
    status: Mapped[str] = mapped_column(String(32), default="DRAFT", index=True)
    max_price: Mapped[float] = mapped_column(Float, default=25.0)
    quoted_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    approval_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    receipt: Mapped[list] = mapped_column(JSON, default=list)
    result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class DealError(RuntimeError):
    pass


def transition(deal: DomainDeal, to: str, note: str = "") -> None:
    if to not in TRANSITIONS.get(deal.status, set()):
        raise DealError(f"illegal transition {deal.status} → {to}")
    deal.status = to
    deal.receipt = [*deal.receipt, {"ts": utcnow().isoformat(), "to": to, "note": note[:300]}]


def mint_approval(deal: DomainDeal) -> str:
    """One-time raw token; only sha256 is stored."""
    if deal.status != "PREPARED":
        raise DealError("approve only from PREPARED")
    raw = secrets.token_hex(16)
    deal.approval_hash = hashlib.sha256(raw.encode()).hexdigest()
    return raw


def check_approval(deal: DomainDeal, raw: str) -> None:
    if deal.status != "APPROVED":
        raise DealError("register only from APPROVED")
    if not deal.approval_hash or not hmac.compare_digest(deal.approval_hash, hashlib.sha256(raw.encode()).hexdigest()):
        raise DealError("bad approval token")


def price_ok(quoted: float | None, prepared: float | None, max_price: float, drift_pct: float = 10.0) -> tuple[bool, str]:
    """Drift guard + budget cap. Fail closed on missing prices."""
    if quoted is None or prepared is None:
        return False, "missing price — refusing to buy blind"
    if quoted > max_price:
        return False, f"£/{quoted} exceeds max {max_price}"
    drift = abs(quoted - prepared) / max(prepared, 0.01) * 100
    if drift > drift_pct:
        return False, f"price drifted {drift:.1f}% since prepare"
    return True, "ok"
