"""Backend setup + webhooks: Telnyx, LiveKit config, Google Calendar.

This is the agent-managed backend panel: every provider is provisioned,
wired and reconciled from here. Secrets land in the encrypted vault, never
in the kernel. Voice agent consumes: sip-config, voice-webhook, slots.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import gcal, livekit_cfg, telephony
from .vault import CredentialVault

router = APIRouter(prefix="/api/backend", tags=["backend"])


def _db():
    from .db import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _vault(db: Session) -> CredentialVault:
    return CredentialVault(db)


def _kernel(db: Session, slug: str) -> tuple[Any, dict]:
    from .models import Project
    from .tradie import TradieKernel

    p = db.scalar(select(Project).where(Project.slug == slug))
    if p is None:
        raise HTTPException(404, f"unknown business {slug}")
    k = db.scalar(select(TradieKernel).where(TradieKernel.project_id == p.id))
    return p, ((k.config if k else {}) or {})


# ---- Telnyx setup ----

class TelnyxKey(BaseModel):
    api_key: str


@router.post("/{slug}/telnyx/credential")
def telnyx_save_key(slug: str, body: TelnyxKey, db: Session = Depends(_db)):
    _vault(db).set_credential(slug, "telnyx", "api_key", body.api_key)
    return {"ok": True}


@router.get("/{slug}/telnyx/numbers")
def telnyx_numbers(slug: str, country: str = "GB", db: Session = Depends(_db)):
    key = _vault(db).get_credential(slug, "telnyx", "api_key")
    if not key:
        raise HTTPException(409, "no telnyx api_key — POST it to /telnyx/credential first (SKILL.md)")
    try:
        return {"owned": telephony.list_numbers(key), "available": telephony.search_numbers(key, country)}
    except telephony.TelnyxError as e:
        raise HTTPException(502, str(e)[:300])


class TelnyxWire(BaseModel):
    connection_id: str
    phone_number: str
    base_url: str  # public brain URL, e.g. https://steve.example.com


@router.post("/{slug}/telnyx/wire")
def telnyx_wire(slug: str, body: TelnyxWire, db: Session = Depends(_db)):
    """Store connection+number, point Telnyx webhooks at the brain. One call wires voice+SMS."""
    from .tradie import TradieKernel

    v = _vault(db)
    key = v.get_credential(slug, "telnyx", "api_key")
    if not key:
        raise HTTPException(409, "no telnyx api_key")
    p, kernel = _kernel(db, slug)
    hook = f"{body.base_url.rstrip('/')}/api/backend/telnyx/voice-webhook?slug={slug}"
    sms_hook = f"{body.base_url.rstrip('/')}/api/backend/telnyx/sms-webhook?slug={slug}"
    try:
        app = telephony.set_voice_webhook(key, body.connection_id, hook)
    except telephony.TelnyxError as e:
        raise HTTPException(502, f"telnyx rejected webhook: {str(e)[:200]}")
    v.set_credential(slug, "telnyx", "connection_id", body.connection_id)
    v.set_credential(slug, "telnyx", "phone_number", body.phone_number)
    k = db.scalar(select(TradieKernel).where(TradieKernel.project_id == p.id))
    cfg = dict(kernel)
    cfg["telnyx"] = {"phone_number": body.phone_number, "voice_webhook": hook, "sms_webhook": sms_hook}
    if k is None:
        db.add(TradieKernel(project_id=p.id, config=cfg))
    else:
        k.config = cfg
    db.commit()
    return {"ok": True, "voice_webhook": hook, "sms_webhook": sms_hook,
            "telnyx_app": {"id": app.get("id"), "webhook": app.get("webhook_event_url")}}


@router.post("/telnyx/voice-webhook")
async def telnyx_voice_webhook(payload: dict[str, Any], slug: str = "", db: Session = Depends(_db)):
    """Call events → jobs. hangup/completed with transcript opens the intake;
    recording URLs attach to the job."""
    from .models import HumanAction, Project
    from .tradie import Job, JobMessage

    ev = telephony.parse_call_event(payload)
    if ev is None:
        return {"ok": True, "ignored": True}
    p = db.scalar(select(Project).where(Project.slug == slug)) if slug else None
    if p is None:
        # match by called number across kernels
        from .tradie import TradieKernel

        for proj, cfg in db.execute(select(Project, TradieKernel.config).join(
                TradieKernel, TradieKernel.project_id == Project.id)).all():
            if isinstance(cfg, dict) and (cfg.get("telnyx") or {}).get("phone_number") == ev["to"]:
                p = proj
                break
    if p is None:
        raise HTTPException(404, "no business for this call")
    if ev["kind"] != "completed":
        return {"ok": True, "kind": ev["kind"], "note": "jobs open on completed calls"}
    job = Job(project_id=p.id, customer_name="", customer_phone=ev["from"] or "",
              channel="voice", job_type="general",
              description=f"Inbound call {ev['duration_sec'] or '?'}s"
                          + (f"\nRecording: {ev['recording_url']}" if ev["recording_url"] else "")
                          + (f"\n{ev['transcript']}" if ev["transcript"] else ""),
              status="new", extra={"call_id": ev["call_id"], "intake_state": "open"})
    db.add(job)
    db.flush()
    if ev["transcript"]:
        db.add(JobMessage(job_id=job.id, role="customer", channel="voice", content=ev["transcript"]))
    db.add(HumanAction(project_id=p.id, resource_key=f"job:{job.id}",
                       title=f"📞 Call from {ev['from'] or 'unknown'} ({ev['duration_sec'] or '?'}s)",
                       instructions=f"Call transcript/recording on job #{job.id}. Quote + options via job view.",
                       priority=70))
    db.commit()
    return {"ok": True, "job_id": job.id}


@router.post("/telnyx/sms-webhook")
async def telnyx_sms_webhook(payload: dict[str, Any], slug: str = "", db: Session = Depends(_db)):
    """Inbound SMS → same continuity rule as WhatsApp (append to open job)."""
    from .models import Project
    from .tradie import Job, JobMessage

    from datetime import timedelta

    from .tradie import utcnow

    msg = telephony.parse_sms_event(payload)
    if msg is None:
        return {"ok": True, "ignored": True}
    p = db.scalar(select(Project).where(Project.slug == slug)) if slug else db.scalar(
        select(Project).order_by(Project.id))
    cutoff = utcnow() - timedelta(days=30)
    job = db.scalar(select(Job).where(
        Job.project_id == p.id, Job.customer_phone == msg["from"],
        Job.status.not_in(("done", "invoiced", "lost")), Job.created_at >= cutoff
    ).order_by(Job.id.desc())) if msg["from"] else None
    if job is None:
        job = Job(project_id=p.id, customer_phone=msg["from"], channel="sms",
                  description=msg["text"], status="new")
        db.add(job)
        db.flush()
    else:
        job.description = ((job.description + "\n" + msg["text"]) if job.description else msg["text"])[:2000]
    db.add(JobMessage(job_id=job.id, role="customer", channel="sms", content=msg["text"]))
    db.commit()
    return {"ok": True, "job_id": job.id}


# ---- LiveKit handoff (config the voice agent applies) ----

@router.get("/{slug}/livekit/sip-config")
def livekit_sip_config(slug: str, livekit_sip_host: str = "sip.livekit.cloud",
                       agent_name: str = "sparky-voice", db: Session = Depends(_db)):
    v = _vault(db)
    number = v.get_credential(slug, "telnyx", "phone_number")
    if not number:
        raise HTTPException(409, "no telnyx phone_number — wire Telnyx first")
    cfg = livekit_cfg.sip_trunk_config(number, livekit_sip_host, agent_name=agent_name)
    return {"config": cfg, "problems": livekit_cfg.validate_sip_config(cfg)}


# ---- Google Calendar ----

class GcalCreds(BaseModel):
    client_id: str
    client_secret: str
    redirect_uri: str


@router.post("/{slug}/gcal/auth-url")
def gcal_auth_url(slug: str, body: GcalCreds, db: Session = Depends(_db)):
    _vault(db).set_credential(slug, "google", "client_id", body.client_id)
    _vault(db).set_credential(slug, "google", "client_secret", body.client_secret)
    _vault(db).set_credential(slug, "google", "redirect_uri", body.redirect_uri)
    return {"auth_url": gcal.auth_url(body.client_id, body.redirect_uri, state=slug)}


class GcalCode(BaseModel):
    code: str


@router.post("/{slug}/gcal/callback")
def gcal_callback(slug: str, body: GcalCode, db: Session = Depends(_db)):
    v = _vault(db)
    cid, csec, ruri = (v.get_credential(slug, "google", k) for k in ("client_id", "client_secret", "redirect_uri"))
    if not (cid and csec and ruri):
        raise HTTPException(409, "start at /gcal/auth-url first")
    try:
        d = gcal.exchange_code(cid, csec, ruri, body.code)
    except Exception as e:
        raise HTTPException(502, f"google rejected code: {str(e)[:200]}")
    import time

    v.set_credential(slug, "google", "refresh_token", d["refresh_token"])
    v.set_credential(slug, "google", "access_token", d["access_token"])
    v.set_credential(slug, "google", "access_expires", str(time.time() + int(d.get("expires_in", 3600))))
    return {"ok": True}


@router.get("/{slug}/gcal/status")
def gcal_status(slug: str, db: Session = Depends(_db)):
    v = _vault(db)
    return {"connected": bool(v.get_credential(slug, "google", "refresh_token")),
            "calendar_id": v.get_credential(slug, "google", "calendar_id")}


class GcalCal(BaseModel):
    calendar_id: str


@router.post("/{slug}/gcal/calendar")
def gcal_set_calendar(slug: str, body: GcalCal, db: Session = Depends(_db)):
    _vault(db).set_credential(slug, "google", "calendar_id", body.calendar_id)
    return {"ok": True}
