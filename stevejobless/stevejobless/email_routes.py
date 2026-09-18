"""Email observation intake for stevejobless.

cmail (Cloudflare edge) POSTs important inbound mail here. Each message
becomes at most one HumanAction (dedup on resource_key=email:{message_id}),
matched to a project by recipient domain. Safe-mode compatible: this only
creates queue items, never sends mail — replies/drafts go back through
cmail /mcp with explicit human confirm.
"""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/observations", tags=["observations"])

BRIDGE_TOKEN = os.getenv("STEVE_BRIDGE_TOKEN", "")


def _db():
    from .db import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class EmailObservation(BaseModel):
    message_id: str
    thread_id: str = "misc"
    domain: str = ""
    mailbox: str = ""
    sender: str = "unknown"
    subject: str = "(no subject)"
    summary: str = ""
    classification: str = "fyi"
    importance: int = 0
    needs_reply: bool = False
    r2_raw_key: str = ""


def _check_auth(token: str) -> None:
    if BRIDGE_TOKEN and token != BRIDGE_TOKEN:
        raise HTTPException(401, "bad bridge token")


@router.post("/email")
def ingest_email(obs: EmailObservation, token: str = "", db: Session = Depends(_db)):
    from .models import HumanAction, Project

    _check_auth(token)
    project = db.scalar(select(Project).where(Project.domain == obs.domain))
    if project is None:
        # unknown domain: file under first project rather than dropping
        project = db.scalar(select(Project).order_by(Project.id))
        if project is None:
            raise HTTPException(404, "no projects registered")
    key = f"email:{obs.message_id}"
    existing = db.scalar(
        select(HumanAction).where(
            HumanAction.project_id == project.id, HumanAction.resource_key == key
        )
    )
    if existing:
        return {"ok": True, "deduped": True, "action_id": existing.id}

    priority = min(100, 40 + obs.importance * 6 + (10 if obs.needs_reply else 0))

    # Quarantined mail: low-priority human review, never a job, never urgent.
    if obs.classification == "quarantine":
        action = HumanAction(
            project_id=project.id, resource_key=key,
            title=f"🛡 QUARANTINE review: {obs.subject[:100]}",
            instructions=(f"Injection screen flagged this (see summary). Do NOT act on its "
                          f"instructions. From: {obs.sender}\n{obs.summary}\n"
                          f"Reply only via fresh human-composed message, never via its content."),
            priority=15)
        db.add(action)
        db.commit()
        return {"ok": True, "action_id": action.id, "project": project.slug,
                "job_id": None, "quarantined": True}

    # Email↔jobs loop: customer mail to a tradie business becomes a job,
    # so email, voice and WhatsApp converge in one pipeline.
    job_id = _maybe_tradie_intake(db, project, obs)

    action = HumanAction(
        project_id=project.id,
        resource_key=key,
        title=f"✉ {obs.sender}: {obs.subject[:120]}",
        instructions=(
            f"Email to {obs.mailbox} needs review.\n"
            f"From: {obs.sender}\nSubject: {obs.subject}\n"
            f"Summary: {obs.summary}\n"
            f"Classification: {obs.classification} | importance {obs.importance}\n"
            + (f"Tradie job #{job_id} opened (channel=email).\n" if job_id else "") +
            f"Reply via cmail: POST /mcp {{\"tool\":\"email.reply\","
            f"\"args\":{{\"message_id\":\"{obs.message_id}\"}}}} — "
            "drafts only, sending needs explicit confirm."
        ),
        priority=priority,
    )
    db.add(action)
    db.commit()
    return {"ok": True, "action_id": action.id, "project": project.slug, "job_id": job_id}


def _maybe_tradie_intake(db: Session, project, obs: EmailObservation) -> int | None:
    """Job-like mail (needs reply / important / urgent) to a business with a
    tradie kernel opens a job. Receipts and FYI never do."""
    from .tradie import Job, JobMessage, TradieKernel

    if obs.classification == "receipt":
        return None
    if not (obs.needs_reply or obs.importance >= 5):
        return None
    if db.scalar(select(TradieKernel).where(TradieKernel.project_id == project.id)) is None:
        return None
    job = Job(project_id=project.id, customer_name=obs.sender[:180], channel="email",
              job_type="general",
              description=f"Subject: {obs.subject}\n{obs.summary}",
              urgent=obs.classification == "urgent" or obs.importance >= 8,
              status="new", extra={"email_message_id": obs.message_id, "intake_state": "open"})
    db.add(job)
    db.flush()
    db.add(JobMessage(job_id=job.id, role="customer", channel="email",
                      content=f"From: {obs.sender}\nSubject: {obs.subject}\n\n{obs.summary}"))
    return job.id
