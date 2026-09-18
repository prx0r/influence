"""Unified read-only MCP (A3, phase 1 of docs/MCP.md).

One JSON-RPC endpoint proxying read-only tools across the stack. Writes stay
on REST behind approvals — this surface can never spend, send, or mutate.
Same permission posture as cmail /mcp: read-only, quarantined mail excluded.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

router = APIRouter(prefix="/mcp", tags=["mcp"])


def _db():
    from .db import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


TOOLS = [
    {"name": "job.list", "description": "List jobs for a business",
     "inputSchema": {"type": "object", "properties": {"slug": {"type": "string"}, "status": {"type": "string"}}, "required": ["slug"]}},
    {"name": "job.get", "description": "Job detail + transcript + quotes + options",
     "inputSchema": {"type": "object", "properties": {"slug": {"type": "string"}, "job_id": {"type": "integer"}}, "required": ["slug", "job_id"]}},
    {"name": "name.check", "description": "Domain availability + live prices (checker prefilter + providers)",
     "inputSchema": {"type": "object", "properties": {"domain": {"type": "string"}}, "required": ["domain"]}},
    {"name": "name.handles", "description": "Handle map across socials/packages/ENS",
     "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
    {"name": "biz.status", "description": "Reconcile states for a business (no writes)",
     "inputSchema": {"type": "object", "properties": {"slug": {"type": "string"}}, "required": ["slug"]}},
    {"name": "email.needs_reply", "description": "Important unread mail proxied from cmail (quarantine excluded)",
     "inputSchema": {"type": "object", "properties": {}}},
]


def _project(db: Session, slug: str):
    from .models import Project

    p = db.scalar(select(Project).where(Project.slug == slug))
    if p is None:
        return {"error": f"unknown business {slug}"}
    return p


@router.post("")
def mcp(body: dict[str, Any], db: Session = Depends(_db)):
    method, params, rid = body.get("method"), body.get("params", {}), body.get("id")
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}}
    if method != "tools/call":
        return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": "method not found"}}
    name, args = params.get("name"), params.get("arguments", {})
    try:
        result = _CALLS[name](db, args)
    except KeyError:
        return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32602, "message": f"unknown tool {name}"}}
    except Exception as e:
        return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32000, "message": str(e)[:200]}}
    return {"jsonrpc": "2.0", "id": rid, "result": {"content": [{"type": "text", "text": str(result)[:8000]}]}}


def _job_list(db: Session, a: dict) -> Any:
    from .tradie import Job

    p = _project(db, a["slug"])
    if isinstance(p, dict):
        return p
    q = select(Job).where(Job.project_id == p.id).order_by(Job.id.desc()).limit(50)
    if a.get("status"):
        q = q.where(Job.status == a["status"])
    return [{"id": j.id, "customer": j.customer_name, "job_type": j.job_type,
             "status": j.status, "urgent": j.urgent, "score": j.score}
            for j in db.scalars(q)]


def _job_get(db: Session, a: dict) -> Any:
    from .tradie import Job, JobMessage, Quote

    p = _project(db, a["slug"])
    if isinstance(p, dict):
        return p
    job = db.scalar(select(Job).where(Job.id == a["job_id"], Job.project_id == p.id))
    if not job:
        return {"error": "no such job"}
    return {"job": {"id": job.id, "customer": job.customer_name, "job_type": job.job_type,
                    "status": job.status, "quoted": job.quoted_price},
            "messages": len(db.scalars(select(JobMessage).where(JobMessage.job_id == job.id)).all()),
            "quotes": [{"id": q.id, "total": q.total, "status": q.status}
                       for q in db.scalars(select(Quote).where(Quote.job_id == job.id))]}


def _name_check(db: Session, a: dict) -> Any:
    from fastapi import HTTPException

    from . import domain_routes as dr

    for provider in ("namecom", "porkbun", "cloudflare"):
        try:
            return dr.check(a["domain"], provider, db)
        except HTTPException:
            continue
    return {"error": "no provider configured — save creds via /api/domains/creds"}


def _name_handles(db: Session, a: dict) -> Any:
    import json as _json
    from urllib.request import Request, urlopen

    req = Request(f"https://domainnamechecker.tradesprior.workers.dev/api/handles/{a['name']}",
                  headers={"User-Agent": "stevejobless-mcp/0.5"})
    with urlopen(req, timeout=30) as resp:
        return _json.loads(resp.read())


def _biz_status(db: Session, a: dict) -> Any:
    from . import tradie_routes as tr

    p = _project(db, a["slug"])
    if isinstance(p, dict):
        return p
    return tr.reconcile_tradie(a["slug"], db)


def _email_needs(db: Session, a: dict) -> Any:
    import json as _json
    import os
    from urllib.request import Request, urlopen

    cmail = os.getenv("CMAIL_URL", "https://cmail.tradesprior.workers.dev")
    req = Request(f"{cmail}/mcp", data=_json.dumps(
        {"tool": "email.needs_reply", "args": {}, "actor": "owner"}).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "stevejobless-mcp/0.5"},
        method="POST")
    with urlopen(req, timeout=20) as resp:
        return _json.loads(resp.read())


_CALLS = {"job.list": _job_list, "job.get": _job_get, "name.check": _name_check,
          "name.handles": _name_handles, "biz.status": _biz_status,
          "email.needs_reply": _email_needs}
