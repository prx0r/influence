"""Tradie routes — jobs, kernel, intake (voice-compat), quotes, actions, stats."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import channels
from .availability import find_slots
from .tradie import JOB_STATUS, Job, JobMessage, Quote, TradieKernel, build_quote, job_stats, score_job

router = APIRouter(prefix="/api/tradie", tags=["tradie"])


def _db():
    from .db import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _project(db: Session, slug: str):
    from .models import HumanAction, Project

    p = db.scalar(select(Project).where(Project.slug == slug))
    if p is None:
        raise HTTPException(404, f"unknown business {slug}")
    return p, HumanAction


def _kernel(db: Session, project_id: int) -> dict[str, Any]:
    k = db.scalar(select(TradieKernel).where(TradieKernel.project_id == project_id))
    return (k.config if k else {}) or {}


# ---- kernel ----

@router.get("/{slug}/kernel")
def get_kernel(slug: str, db: Session = Depends(_db)):
    p, _ = _project(db, slug)
    return {"slug": slug, "kernel": _kernel(db, p.id)}


@router.put("/{slug}/kernel")
def put_kernel(slug: str, config: dict[str, Any], db: Session = Depends(_db)):
    p, _ = _project(db, slug)
    k = db.scalar(select(TradieKernel).where(TradieKernel.project_id == p.id))
    if k is None:
        k = TradieKernel(project_id=p.id, config=config)
        db.add(k)
    else:
        k.config = config
    db.commit()
    return {"ok": True}


# ---- after-hours intake: THE voice-agent compat endpoint ----

class CallIntake(BaseModel):
    customer_name: str = ""
    customer_phone: str = ""
    customer_address: str = ""
    channel: str = "voice"
    job_type: str = "general"
    description: str = ""
    transcript: str = ""
    urgent: bool = False
    after_hours: bool = False
    distance_km: float | None = None


@router.post("/{slug}/intake")
def intake_call(slug: str, call: CallIntake, db: Session = Depends(_db)):
    """Voice agent POSTs here when a call/chat ends. Creates Job + transcript +
    HumanAction (urgent → wake-now alert). Returns one-click options for the app."""
    from .models import HumanAction

    p, _ = _project(db, slug)
    kernel = _kernel(db, p.id)
    autonomy = kernel.get("autonomy", "observe")
    job = Job(project_id=p.id, customer_name=call.customer_name, customer_phone=call.customer_phone,
              customer_address=call.customer_address, channel=call.channel, job_type=call.job_type,
              description=call.description, urgent=call.urgent,
              distance_km=call.distance_km, status="new",
              extra={"after_hours": call.after_hours, "intake_state": "open"})
    db.add(job)
    db.flush()
    if call.transcript:
        db.add(JobMessage(job_id=job.id, role="customer", channel=call.channel, content=call.transcript))
    # autonomy gating (sara pattern, cleanroom): observe=log only;
    # semi_auto=+draft quote & score; full_auto=+propose slots. Sends always human-confirmed.
    job_dict = call.model_dump()
    if autonomy in ("semi_auto", "full_auto"):
        q = build_quote(kernel, job_dict, _parts_prices(kernel, call.job_type))
        quote = Quote(job_id=job.id, line_items=q["line_items"], total=q["total"], message=q["message"])
        db.add(quote)
        job.quoted_price = q["total"]
        job.status = "quoted"
        s = score_job(kernel, {**job_dict, "quoted_price": q["total"]})
        job.score, job.score_reasons = s["score"], s["reasons"]
    if autonomy == "full_auto":
        job.extra = {**job.extra, "slots": _free_slots(db, p.id, kernel, call.job_type)}
    action = HumanAction(
        project_id=p.id, resource_key=f"job:{job.id}",
        title=f"⚡ {'URGENT ' if call.urgent else ''}{call.job_type}: {call.customer_name or call.customer_phone or 'unknown caller'}",
        instructions=(f"{'WAKE-NOW ALERT — urgent job.\n' if call.urgent else ''}"
                      f"Channel: {call.channel} | {call.customer_address}\n{call.description}\n"
                      f"Transcript on job #{job.id}. Quote + options below."),
        priority=100 if call.urgent else (50 if autonomy == "full_auto" and not call.urgent else 70))
    db.add(action)
    db.commit()
    parts = _parts_prices(kernel, call.job_type)
    job_view = {**job_dict, "quoted_price": job.quoted_price, "slots": (job.extra or {}).get("slots", [])}
    return {"ok": True, "job_id": job.id, "action_id": action.id, "autonomy": autonomy,
            "options": _options(kernel, job.id, job_view, parts)}


def _parts_prices(kernel: dict, job_type: str) -> dict[str, float]:
    from . import parts as parts_mod

    out = {}
    for part in ((kernel.get("price_book") or {}).get(job_type, {}).get("typical_parts") or []):
        r = parts_mod.lookup(part)
        if r.get("price") is not None:
            out[part] = float(r["price"])
    return out


def _free_slots(db: Session, project_id: int, kernel: dict, job_type: str) -> list[dict]:
    # busy windows: assume 2h blocks from scheduled_at (refine with duration stats later)
    from datetime import timedelta, timezone

    def _aware(dt):
        return dt if dt is None or dt.tzinfo else dt.replace(tzinfo=timezone.utc)

    busy = [(j.scheduled_at, j.scheduled_at) for j in
            db.scalars(select(Job).where(Job.project_id == project_id, Job.scheduled_at.is_not(None),
                                         Job.status.not_in(("done", "invoiced", "lost")))).all()]
    windows = [(_aware(b[0]), _aware(b[0]) + timedelta(hours=2)) for b in busy if b[0]]
    live = _gcal_busy(db, project_id, kernel)
    if live is not None:
        windows = live
    return find_slots(kernel, windows)


def _gcal_busy(db: Session, project_id: int, kernel: dict) -> list | None:
    """Live Google freebusy when connected, else None (caller falls back)."""
    from datetime import datetime, timezone

    from . import gcal
    from .models import Project
    from .vault import CredentialVault

    p = db.scalar(select(Project).where(Project.id == project_id))
    if p is None:
        return None
    v = CredentialVault(db)
    cal_id = v.get_credential(p.slug, "google", "calendar_id")
    cid = v.get_credential(p.slug, "google", "client_id")
    csec = v.get_credential(p.slug, "google", "client_secret")
    if not (cal_id and cid and csec):
        return None
    try:
        token = gcal.with_fresh_token(v, p.slug, cid, csec)
        if not token:
            return None
        now = datetime.now(timezone.utc)
        end = now + timedelta(days=8)

        def _aware(dt):
            d = datetime.fromisoformat(dt.replace("Z", "+00:00"))
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)

        return [(_aware(s), _aware(e)) for s, e in
                gcal.freebusy(token, cal_id, now.isoformat(), end.isoformat())]
    except Exception:
        return None


def _backend_checks(db: Session, slug: str) -> dict:
    """Telnyx / LiveKit / Google Calendar readiness for reconcile."""
    from . import livekit_cfg
    from .vault import CredentialVault

    v = CredentialVault(db)
    out: dict = {}
    if v.get_credential(slug, "telnyx", "api_key"):
        number = v.get_credential(slug, "telnyx", "phone_number")
        out["backend:telnyx"] = (("READY", number or "key set, number unwired") if number
                                 else ("MISSING", "key set — wire via POST /backend/{slug}/telnyx/wire"))
    else:
        out["backend:telnyx"] = ("MISSING", "no api_key — POST to /backend/{slug}/telnyx/credential (SKILL.md)")
    number = v.get_credential(slug, "telnyx", "phone_number")
    if number:
        problems = livekit_cfg.validate_sip_config(
            livekit_cfg.sip_trunk_config(number, "sip.livekit.cloud"))
        out["backend:livekit"] = (("READY", f"SIP trunk config valid for {number}") if not problems
                                  else ("MISSING", "; ".join(problems)))
    else:
        out["backend:livekit"] = ("MISSING", "needs Telnyx number first")
    if v.get_credential(slug, "google", "refresh_token"):
        out["backend:gcal"] = (("READY", v.get_credential(slug, "google", "calendar_id") or "connected, pick calendar")
                               if v.get_credential(slug, "google", "calendar_id") else ("MISSING", "connected — POST calendar id"))
    else:
        out["backend:gcal"] = ("MISSING", "Google not connected — POST /backend/{slug}/gcal/auth-url")
    return out


def _options(kernel: dict, job_id: int, job: dict, parts_prices: dict | None = None) -> list[dict[str, Any]]:
    q = build_quote(kernel, job, parts_prices)
    s = score_job(kernel, job)
    opts = [
        {"id": "quote", "label": f"Send quote £{q['total']:.0f}", "kind": "draft",
         "preview": q["message"], "needs_review": q["needs_review"]},
        {"id": "calendar", "label": "Add to calendar", "kind": "ics", "job_id": job_id},
        {"id": "call_back", "label": f"Call {job.get('customer_phone') or 'customer'}", "kind": "tel"},
        {"id": "verdict", "label": f"Agent says: {s['verdict'].upper()} ({s['score']})", "kind": "info",
         "reasons": s["reasons"]},
    ]
    slots = (job.get("slots") or [])
    if slots:
        opts.insert(1, {"id": "slots", "label": f"Offer: {slots[0]['label']}", "kind": "slots", "slots": slots})
    return opts


# ---- jobs ----

@router.get("/{slug}/jobs")
def list_jobs(slug: str, status: str | None = None, db: Session = Depends(_db)):
    p, _ = _project(db, slug)
    q = select(Job).where(Job.project_id == p.id).order_by(Job.id.desc()).limit(100)
    if status:
        q = q.where(Job.status == status)
    return {"jobs": [{"id": j.id, "customer": j.customer_name, "phone": j.customer_phone,
                      "job_type": j.job_type, "status": j.status, "urgent": j.urgent,
                      "quoted": j.quoted_price, "score": j.score,
                      "scheduled_at": j.scheduled_at} for j in db.scalars(q)]}


@router.get("/{slug}/jobs/{job_id}")
def get_job(slug: str, job_id: int, db: Session = Depends(_db)):
    p, _ = _project(db, slug)
    job = db.scalar(select(Job).where(Job.id == job_id, Job.project_id == p.id))
    if not job:
        raise HTTPException(404, "no such job")
    msgs = db.scalars(select(JobMessage).where(JobMessage.job_id == job.id).order_by(JobMessage.id)).all()
    quotes = db.scalars(select(Quote).where(Quote.job_id == job.id).order_by(Quote.id)).all()
    kernel = _kernel(db, p.id)
    return {
        "job": {"id": job.id, "customer": job.customer_name, "phone": job.customer_phone,
                "address": job.customer_address, "job_type": job.job_type,
                "description": job.description, "status": job.status, "urgent": job.urgent,
                "quoted": job.quoted_price, "final": job.final_price, "score": job.score},
        "transcript": [{"role": m.role, "channel": m.channel, "content": m.content} for m in msgs],
        "quotes": [{"id": q.id, "total": q.total, "status": q.status, "message": q.message} for q in quotes],
        "options": _options(kernel, job.id, {"customer_name": job.customer_name,
                                             "customer_phone": job.customer_phone, "job_type": job.job_type,
                                             "distance_km": job.distance_km, "quoted_price": job.quoted_price,
                                             "urgent": job.urgent, "after_hours": (job.extra or {}).get("after_hours"),
                                             "slots": (job.extra or {}).get("slots", [])},
                              _parts_prices(kernel, job.job_type)),    }


class JobPatch(BaseModel):
    status: str | None = None
    scheduled_at: datetime | None = None
    final_price: float | None = None
    duration_min: int | None = None
    note: str | None = None


@router.patch("/{slug}/jobs/{job_id}")
def patch_job(slug: str, job_id: int, patch: JobPatch, db: Session = Depends(_db)):
    p, _ = _project(db, slug)
    job = db.scalar(select(Job).where(Job.id == job_id, Job.project_id == p.id))
    if not job:
        raise HTTPException(404, "no such job")
    if patch.status:
        if patch.status not in JOB_STATUS:
            raise HTTPException(400, f"bad status, want one of {JOB_STATUS}")
        job.status = patch.status
    if patch.scheduled_at:
        job.scheduled_at = patch.scheduled_at
    if patch.final_price is not None:
        job.final_price = patch.final_price
    if patch.duration_min is not None:
        job.duration_min = patch.duration_min
    if patch.note:
        db.add(JobMessage(job_id=job.id, role="tradie", channel="app", content=patch.note))
    db.commit()
    return {"ok": True, "status": job.status}


@router.get("/{slug}/jobs/{job_id}/calendar.ics")
def job_ics(slug: str, job_id: int, db: Session = Depends(_db)):
    p, _ = _project(db, slug)
    job = db.scalar(select(Job).where(Job.id == job_id, Job.project_id == p.id))
    if not job:
        raise HTTPException(404, "no such job")
    start = (job.scheduled_at or datetime.now()).strftime("%Y%m%dT%H%M%S")
    ics = (f"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nBEGIN:VEVENT\r\nUID:job-{job.id}@steve\r\n"
           f"DTSTART:{start}\r\nSUMMARY:{job.job_type} — {job.customer_name}\r\n"
           f"LOCATION:{job.customer_address}\r\nDESCRIPTION:{job.description[:200]}\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n")
    return PlainTextResponse(ics, media_type="text/calendar")


# ---- slots + confirm (intake lifecycle: open → captured → confirmed → closed) ----

@router.get("/{slug}/slots")
def slots(slug: str, job_type: str = "general", duration_min: int = 120, db: Session = Depends(_db)):
    p, _ = _project(db, slug)
    return {"slots": _free_slots(db, p.id, _kernel(db, p.id), job_type)}


class ConfirmIn(BaseModel):
    scheduled_at: datetime
    note: str | None = None


@router.post("/{slug}/jobs/{job_id}/confirm")
def confirm_job(slug: str, job_id: int, body: ConfirmIn, db: Session = Depends(_db)):
    """Customer agreed a slot → capture→confirm: set schedule, status, intake_state."""
    p, _ = _project(db, slug)
    job = db.scalar(select(Job).where(Job.id == job_id, Job.project_id == p.id))
    if not job:
        raise HTTPException(404, "no such job")
    job.scheduled_at = body.scheduled_at
    job.status = "scheduled"
    job.extra = {**(job.extra or {}), "intake_state": "confirmed"}
    if body.note:
        db.add(JobMessage(job_id=job.id, role="agent", channel="app", content=body.note))
    db.commit()
    return {"ok": True, "job_id": job.id, "scheduled_at": job.scheduled_at, "intake_state": "confirmed"}


@router.post("/{slug}/sweep")
def sweep(slug: str, days: int | None = None, confirm: bool = False, db: Session = Depends(_db)):
    """Retention sweeper: purge transcripts older than retention window. Needs confirm:true."""
    from .privacy import retention_sweep

    if not confirm:
        raise HTTPException(400, "pass confirm:true to purge transcripts")
    p, _ = _project(db, slug)
    kernel = _kernel(db, p.id)
    return retention_sweep(db, days or int(kernel.get("retention_days", 90)))


# ---- quotes ----

@router.post("/{slug}/jobs/{job_id}/quote")
def make_quote(slug: str, job_id: int, channel: str = "whatsapp", db: Session = Depends(_db)):
    """Draft a quote from the price book. Draft only — send needs tradie confirm."""
    p, _ = _project(db, slug)
    job = db.scalar(select(Job).where(Job.id == job_id, Job.project_id == p.id))
    if not job:
        raise HTTPException(404, "no such job")
    kernel = _kernel(db, p.id)
    q = build_quote(kernel, {"customer_name": job.customer_name, "job_type": job.job_type,
                             "distance_km": job.distance_km,
                             "after_hours": (job.extra or {}).get("after_hours")},
                    _parts_prices(kernel, job.job_type))
    quote = Quote(job_id=job.id, line_items=q["line_items"], total=q["total"], message=q["message"])
    job.quoted_price = q["total"]
    if job.status == "new":
        job.status = "quoted"
    db.add(quote)
    db.commit()
    return {"ok": True, "quote_id": quote.id, "total": q["total"], "message": q["message"],
            "needs_review": q["needs_review"], "channel": channel, "live_send": False,
            "note": "draft only — tradie confirms before anything goes out"}


@router.post("/{slug}/jobs/{job_id}/quote/{quote_id}/send")
def send_quote(slug: str, job_id: int, quote_id: int, db: Session = Depends(_db)):
    """Explicit confirm path: tradie approved → send via WhatsApp (or stub).
    Money-move call-back rule: quotes at/above the kernel threshold need a
    voice confirm on the KNOWN customer number first (mark via /callback),
    so a hijacked chat thread alone can never release money."""
    p, _ = _project(db, slug)
    kernel = _kernel(db, p.id)
    quote = db.scalar(select(Quote).where(Quote.id == quote_id, Quote.job_id == job_id))
    if not quote:
        raise HTTPException(404, "no such quote")
    job = db.scalar(select(Job).where(Job.id == job_id))
    threshold = float(kernel.get("callback_threshold", 500))
    if quote.total >= threshold and not (job.extra or {}).get("callback_verified"):
        raise HTTPException(409, f"£{quote.total:.0f} ≥ £{threshold:.0f} call-back threshold — "
                                 f"verify by voice on the known number, then POST /jobs/{job_id}/callback")
    res = channels.send_whatsapp(job.customer_phone, quote.message) if job.customer_phone else {"ok": False, "stubbed": True, "note": "no customer phone"}
    quote.status = "sent" if res.get("ok") and not res.get("stubbed") else "approved"
    db.commit()
    return {"ok": True, "quote_status": quote.status, "channel_result": res}


class CallbackIn(BaseModel):
    verifier: str = ""  # who confirmed, e.g. "tradie:voice:+447…"
    note: str = ""


@router.post("/{slug}/jobs/{job_id}/callback")
def mark_callback(slug: str, job_id: int, body: CallbackIn, db: Session = Depends(_db)):
    """Record a voice call-back verification on the known customer number."""
    p, _ = _project(db, slug)
    job = db.scalar(select(Job).where(Job.id == job_id, Job.project_id == p.id))
    if not job:
        raise HTTPException(404, "no such job")
    job.extra = {**(job.extra or {}), "callback_verified": True,
                 "callback_by": body.verifier[:120], "callback_note": body.note[:300]}
    db.add(JobMessage(job_id=job.id, role="tradie", channel="app",
                      content=f"call-back verified by {body.verifier[:120]}"))
    db.commit()
    return {"ok": True, "callback_verified": True}


# ---- stats + feed scoring ----

@router.get("/{slug}/stats")
def stats(slug: str, db: Session = Depends(_db)):
    from .tradie import calibration

    p, _ = _project(db, slug)
    jobs = [{"job_type": j.job_type, "status": j.status, "duration_min": j.duration_min,
             "final_price": j.final_price, "quoted_price": j.quoted_price}
            for j in db.scalars(select(Job).where(Job.project_id == p.id))]
    scored = [{"status": j.status, "final_price": j.final_price,
               "quoted_price": j.quoted_price, "score": j.score}
              for j in db.scalars(select(Job).where(Job.project_id == p.id))]
    return {"stats": job_stats(jobs), "calibration": calibration(scored), "total": len(jobs)}


@router.post("/{slug}/score")
def score(slug: str, job: dict[str, Any], db: Session = Depends(_db)):
    """Score any candidate job (feed item or inbound lead) against this tradie's kernel."""
    p, _ = _project(db, slug)
    kernel = _kernel(db, p.id)
    done = [{"job_type": j.job_type, "status": j.status, "duration_min": j.duration_min,
             "final_price": j.final_price, "quoted_price": j.quoted_price}
            for j in db.scalars(select(Job).where(Job.project_id == p.id))]
    return score_job(kernel, job, job_stats(done))


# ---- job feed: same feed, per-tradie order (insta-algo for jobs) ----

@router.get("/feed")
def feed(for_slug: str, db: Session = Depends(_db)):
    """Open leads across ALL tradie businesses, scored + ordered for `for_slug`.
    The marketplace primitive: one feed, every contractor's algo ranks it
    differently by calendar, prefs and stats."""
    from .models import Project
    from .tradie import TradieKernel, calibration

    consumer_p = db.scalar(select(Project).where(Project.slug == for_slug))
    if consumer_p is None:
        raise HTTPException(404, f"unknown business {for_slug}")
    kernel = _kernel(db, consumer_p.id)
    done = [{"job_type": j.job_type, "status": j.status, "duration_min": j.duration_min,
             "final_price": j.final_price, "quoted_price": j.quoted_price}
            for j in db.scalars(select(Job).where(Job.project_id == consumer_p.id))]
    stats = job_stats(done)
    items = []
    for job, proj in db.execute(select(Job, Project).join(Project, Job.project_id == Project.id)
                                .where(Job.status.in_(("new", "qualified", "quoted")))).all():
        if db.scalar(select(TradieKernel).where(TradieKernel.project_id == proj.id)) is None:
            continue
        s = score_job(kernel, {"job_type": job.job_type, "distance_km": job.distance_km,
                               "quoted_price": job.quoted_price, "urgent": job.urgent})
        items.append({"job_id": job.id, "business": proj.slug, "job_type": job.job_type,
                      "description": (job.description or "")[:160], "urgent": job.urgent,
                      "mine": proj.slug == for_slug, **s})
    items.sort(key=lambda i: -i["score"])
    return {"for": for_slug, "items": items, "calibration": calibration(
        [{**d, "score": j.score} for d, j in
         (({"status": j.status, "final_price": j.final_price, "quoted_price": j.quoted_price}, j)
          for j in db.scalars(select(Job).where(Job.project_id == consumer_p.id)))])}


# ---- invoicing lite (tax stepping stone) ----

@router.post("/{slug}/jobs/{job_id}/invoice")
def make_invoice(slug: str, job_id: int, db: Session = Depends(_db)):
    from .tradie import Invoice

    p, _ = _project(db, slug)
    job = db.scalar(select(Job).where(Job.id == job_id, Job.project_id == p.id))
    if not job:
        raise HTTPException(404, "no such job")
    quote = db.scalars(select(Quote).where(Quote.job_id == job.id).order_by(Quote.id.desc())).first()
    lines = quote.line_items if quote else []
    total = job.final_price or job.quoted_price or (quote.total if quote else 0)
    kernel = _kernel(db, p.id)
    vat_rate = float(kernel.get("vat_rate", 0.2))
    inv = Invoice(job_id=job.id, number=f"{p.slug.upper()}-{job.id:04d}",
                  line_items=lines, total=round(total or 0, 2),
                  vat_rate=vat_rate, vat_amount=round((total or 0) * vat_rate, 2))
    db.add(inv)
    if job.status == "done":
        job.status = "invoiced"
    db.commit()
    return {"ok": True, "invoice_id": inv.id, "number": inv.number, "total": inv.total,
            "vat": inv.vat_amount, "gross": round(inv.total + inv.vat_amount, 2)}


@router.get("/{slug}/invoices")
def list_invoices(slug: str, db: Session = Depends(_db)):
    from .tradie import Invoice

    p, _ = _project(db, slug)
    invs = db.execute(select(Invoice, Job).join(Job, Invoice.job_id == Job.id)
                      .where(Job.project_id == p.id).order_by(Invoice.id.desc())).all()
    return {"invoices": [{"id": i.id, "number": i.number, "job_id": j.id, "customer": j.customer_name,
                          "total": i.total, "status": i.status} for i, j in invs]}


@router.get("/{slug}/invoices.csv")
def invoices_csv(slug: str, db: Session = Depends(_db)):
    import csv
    import io

    from .tradie import Invoice

    p, _ = _project(db, slug)
    invs = db.execute(select(Invoice, Job).join(Job, Invoice.job_id == Job.id)
                      .where(Job.project_id == p.id).order_by(Invoice.id)).all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["number", "customer", "job_type", "total", "vat", "gross", "status", "created"])
    for i, j in invs:
        w.writerow([i.number, j.customer_name, j.job_type, i.total, i.vat_amount,
                    round((i.total or 0) + (i.vat_amount or 0), 2), i.status, i.created_at])
    return PlainTextResponse(buf.getvalue(), media_type="text/csv")


@router.get("/{slug}/tax/quarter")
def tax_quarter(slug: str, year: int | None = None, q: int | None = None, db: Session = Depends(_db)):
    """Quarterly VAT/revenue summary for the accountant. Defaults to current quarter."""
    from datetime import date

    from .tradie import Invoice

    from sqlalchemy import extract

    today = date.today()
    year = year or today.year
    q = q or ((today.month - 1) // 3 + 1)
    months = list(range((q - 1) * 3 + 1, q * 3 + 1))
    p, _ = _project(db, slug)
    invs = db.execute(select(Invoice, Job).join(Job, Invoice.job_id == Job.id)
                      .where(Job.project_id == p.id,
                             extract("year", Invoice.created_at) == year,
                             extract("month", Invoice.created_at).in_(months))).all()
    net = round(sum(i.total or 0 for i, _ in invs), 2)
    vat = round(sum(i.vat_amount or 0 for i, _ in invs), 2)
    return {"slug": slug, "year": year, "quarter": q, "invoices": len(invs),
            "net": net, "vat_owed": vat, "gross": round(net + vat, 2)}


# ---- quote → cmail email draft (drafts queue in cmail until send/paid) ----

@router.post("/{slug}/jobs/{job_id}/quote/{quote_id}/email_draft")
def quote_email_draft(slug: str, job_id: int, quote_id: int, to: str = "", db: Session = Depends(_db)):
    import json as _json
    import os
    from urllib.request import Request, urlopen

    p, _ = _project(db, slug)
    quote = db.scalar(select(Quote).where(Quote.id == quote_id, Quote.job_id == job_id))
    if not quote:
        raise HTTPException(404, "no such quote")
    cmail = os.getenv("CMAIL_URL", "https://cmail.tradesprior.workers.dev")
    secret = os.getenv("CMAIL_DRAFT_SECRET", "")
    try:
        req = Request(f"{cmail}/api/drafts",
                      data=_json.dumps({"secret": secret, "to": to,
                                        "subject": f"Quote from {p.name}",
                                        "body": quote.message}).encode(),
                      headers={"Content-Type": "application/json",
                               "User-Agent": "stevejobless-bridge/0.3"}, method="POST")
        with urlopen(req, timeout=15) as resp:
            d = _json.loads(resp.read())
    except Exception as e:
        raise HTTPException(502, f"cmail unreachable: {str(e)[:120]}")
    # drafts never auto-send: quote status only changes on the explicit send path
    db.commit()
    return {"ok": True, "draft": d}


# ---- tradie reconciliation: desired vs observed on channels ----

@router.post("/{slug}/reconcile")
def reconcile_tradie(slug: str, db: Session = Depends(_db)):
    """Reconcile the tradie's channels: kernel present? WhatsApp live or stub?
    cmail bridge reachable? Each becomes a ResourceState (READY/MISSING/ERROR)."""
    import os
    from urllib.request import Request, urlopen

    from . import channels
    from .models import ResourceState

    p, _ = _project(db, slug)
    kernel = _kernel(db, p.id)
    checks = {
        "kernel": ("READY" if kernel.get("price_book") else "MISSING",
                   "price book loaded" if kernel.get("price_book") else "PUT /kernel first (SKILL.md step 2)"),
        "channel:whatsapp": ("READY" if channels.whatsapp_configured() else "MISSING",
                             "live sends" if channels.whatsapp_configured() else "stub mode — set WHATSAPP_* creds"),
        "channel:voice": ("READY", "compat contract docs/VOICE_COMPAT.md"),
    }
    checks.update(_backend_checks(db, p.slug))
    try:
        from sqlalchemy import func as _func

        from .domain_deals import DomainDeal as _Deal

        open_deals = db.scalar(select(_func.count()).select_from(_Deal).where(
            _Deal.status.in_(("PREPARED", "APPROVED", "REGISTERED")))) or 0
        checks["backend:domains"] = (("READY", f"{open_deals} open deals — /api/domains/*")
                                     if open_deals else ("READY", "no open deals — /api/domains/check to start"))
    except Exception:
        checks["backend:domains"] = ("MISSING", "domain engine unavailable")
    try:
        cmail = os.getenv("CMAIL_URL", "https://cmail.tradesprior.workers.dev")
        req = Request(f"{cmail}/api/stats", headers={"User-Agent": "stevejobless-reconcile/0.3"})
        with urlopen(req, timeout=8) as resp:
            checks["channel:email"] = ("READY", f"cmail bridge ok: {resp.read()[:80].decode(errors='replace')}")
    except Exception as e:
        checks["channel:email"] = ("ERROR", f"cmail unreachable: {str(e)[:100]}")
    for key, (status, message) in checks.items():
        row = db.scalar(select(ResourceState).where(
            ResourceState.project_id == p.id, ResourceState.key == key))
        if row is None:
            row = ResourceState(project_id=p.id, key=key, kind="channel", label=key,
                                desired={}, observed={})
            db.add(row)
        row.status, row.message = status, message
    db.commit()
    return {"slug": slug, "channels": {k: {"status": s, "message": m} for k, (s, m) in checks.items()}}


class SmsIn(BaseModel):
    text: str


@router.post("/{slug}/jobs/{job_id}/sms")
def sms_confirm(slug: str, job_id: int, body: SmsIn, db: Session = Depends(_db)):
    """SMS confirm / on-my-way message. Real delivery with Telnyx creds, honest stub without."""
    from .vault import CredentialVault

    p, _ = _project(db, slug)
    job = db.scalar(select(Job).where(Job.id == job_id, Job.project_id == p.id))
    if not job:
        raise HTTPException(404, "no such job")
    if not job.customer_phone:
        raise HTTPException(400, "no customer phone on this job")
    v = CredentialVault(db)
    res = channels.send_sms(job.customer_phone, body.text,
                            api_key=v.get_credential(slug, "telnyx", "api_key"),
                            from_number=v.get_credential(slug, "telnyx", "phone_number"),
                            profile_id=v.get_credential(slug, "telnyx", "messaging_profile_id"))
    db.add(JobMessage(job_id=job.id, role="agent", channel="sms",
                      content=body.text + (" [stubbed]" if res.get("stubbed") else " [sent]")))
    db.commit()
    return {"ok": res.get("ok", False), "result": res}


# ---- Instagram inbox bridge (DMs → leads, same continuity rule) ----

@router.get("/instagram/webhook")
def ig_verify(hub_mode: str = "", hub_verify_token: str = "", hub_challenge: str = ""):
    import os

    if hub_verify_token == os.getenv("INSTAGRAM_VERIFY_TOKEN", "") and os.getenv("INSTAGRAM_VERIFY_TOKEN"):
        return PlainTextResponse(hub_challenge)
    raise HTTPException(403, "bad verify token")


@router.post("/instagram/webhook")
async def ig_inbound(payload: dict[str, Any], db: Session = Depends(_db)):
    from datetime import timedelta

    from .models import Project
    from .tradie import utcnow

    msgs = channels.parse_instagram_webhook(payload)
    p = db.scalar(select(Project).join(TradieKernel, TradieKernel.project_id == Project.id).order_by(Project.id))
    if p is None:
        p = db.scalar(select(Project).order_by(Project.id))
    out = []
    cutoff = utcnow() - timedelta(days=30)
    for m in msgs:
        job = db.scalar(select(Job).where(
            Job.project_id == p.id, Job.customer_phone == m["from"],
            Job.status.not_in(("done", "invoiced", "lost")), Job.created_at >= cutoff
        ).order_by(Job.id.desc())) if m["from"] else None
        if job is None:
            job = Job(project_id=p.id, customer_phone=m["from"], channel="instagram",
                      description=m["text"], status="new")
            db.add(job)
            db.flush()
        else:
            job.description = ((job.description + "\n" + m["text"]) if job.description else m["text"])[:2000]
        db.add(JobMessage(job_id=job.id, role="customer", channel="instagram", content=m["text"]))
        out.append(job.id)
    db.commit()
    return {"ok": True, "jobs": out}


# ---- social claim-verify (human claims, machine verifies + records) ----

SIGNUP_URLS = {
    "github": "https://github.com/signup",
    "x": "https://x.com/i/flow/signup",
    "youtube": "https://www.youtube.com/create_channel",
    "instagram": "https://www.instagram.com/accounts/emailsignup/",
    "tiktok": "https://www.tiktok.com/signup",
}

VERIFY_URLS = {
    "github": "https://github.com/{h}",
    "x": "https://x.com/{h}",
    "youtube": "https://www.youtube.com/@{h}",
}


@router.get("/{slug}/social/claim-kit")
def social_claim_kit(slug: str, name: str, db: Session = Depends(_db)):
    """Availability map (via checker worker) + ordered claim checklist with
    deep links. Claiming itself is human — platforms allow no other way."""
    import json as _json
    from urllib.request import Request, urlopen

    p, _ = _project(db, slug)
    try:
        req = Request(f"https://domainnamechecker.tradesprior.workers.dev/api/handles/{name}",
                      headers={"User-Agent": "stevejobless-bridge/0.3"})
        with urlopen(req, timeout=30) as resp:
            handles = _json.loads(resp.read()).get("handles", [])
    except Exception as e:
        raise HTTPException(502, f"checker unreachable: {str(e)[:120]}")
    steps = []
    for h in handles:
        plat = h["platform"]
        if h["status"] == "available" and plat in SIGNUP_URLS:
            steps.append({"platform": plat, "action": "claim", "at": SIGNUP_URLS[plat],
                          "then": f"POST /api/tradie/{slug}/social/verify"})
        elif h["status"] == "unknown":
            steps.append({"platform": plat, "action": "check manually",
                          "reason": h.get("reason", "")})
    return {"slug": slug, "name": name, "handles": handles, "claim_order": steps}


class SocialVerify(BaseModel):
    platform: str
    handle: str


@router.post("/{slug}/social/verify")
def social_verify(slug: str, body: SocialVerify, db: Session = Depends(_db)):
    """Verify a human-claimed handle resolves, record it as a connected asset."""
    from urllib.request import Request, urlopen

    from .vault import SocialManager

    p, _ = _project(db, slug)
    tmpl = VERIFY_URLS.get(body.platform)
    live = False
    if tmpl:
        try:
            req = Request(tmpl.format(h=body.handle.lstrip("@")),
                          headers={"User-Agent": "stevejobless-bridge/0.3"}, method="GET")
            with urlopen(req, timeout=15) as resp:
                live = resp.status == 200
        except Exception:
            live = False
    mgr = SocialManager(db)
    if live:
        mgr.connect(slug, body.platform, body.handle)
        return {"ok": True, "verified": True, "platform": body.platform, "handle": body.handle}
    return {"ok": True, "verified": False, "platform": body.platform, "handle": body.handle,
            "note": "does not resolve (yet) — claim first, then re-verify"}
@router.get("/whatsapp/webhook")
def wa_verify(hub_mode: str = "", hub_verify_token: str = "", hub_challenge: str = ""):
    import os

    if hub_verify_token == os.getenv("WHATSAPP_VERIFY_TOKEN", "") and os.getenv("WHATSAPP_VERIFY_TOKEN"):
        return PlainTextResponse(hub_challenge)
    raise HTTPException(403, "bad verify token")


@router.post("/whatsapp/webhook")
async def wa_inbound(payload: dict[str, Any], db: Session = Depends(_db)):
    """WhatsApp message → append to the sender's recent open job if any
    (30d window), else open a new job. Prevents one job per message.
    Routes to the project with a tradie kernel (fallback: first project)."""
    from datetime import timedelta

    from .models import Project
    from .tradie import TradieKernel, utcnow

    msgs = channels.parse_whatsapp_webhook(payload)
    p = db.scalar(select(Project).join(TradieKernel, TradieKernel.project_id == Project.id).order_by(Project.id))
    if p is None:
        p = db.scalar(select(Project).order_by(Project.id))
    out = []
    cutoff = utcnow() - timedelta(days=30)
    for m in msgs:
        recent = db.scalar(select(Job).where(
            Job.project_id == p.id, Job.customer_phone == m["from"],
            Job.status.not_in(("done", "invoiced", "lost")),
            Job.created_at >= cutoff).order_by(Job.id.desc())) if m["from"] else None
        if recent is None and m["from"]:
            recent = db.scalar(select(Job).where(
                Job.project_id == p.id, Job.customer_phone == m["from"],
                Job.created_at >= cutoff).order_by(Job.id.desc()))
        if recent is None:
            recent = Job(project_id=p.id, customer_phone=m["from"], channel="whatsapp",
                         description=m["text"], status="new")
            db.add(recent)
            db.flush()
        else:
            recent.description = ((recent.description + "\n" + m["text"]) if recent.description else m["text"])[:2000]
        db.add(JobMessage(job_id=recent.id, role="customer", channel="whatsapp", content=m["text"]))
        out.append(recent.id)
    db.commit()
    return {"ok": True, "jobs": out}
