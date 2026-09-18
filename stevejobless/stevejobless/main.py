from __future__ import annotations

from datetime import datetime, timezone
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import SessionLocal, init_db
from .engine import project_summary, reconcile_all, reconcile_project, run_autopilot_all, run_autopilot_project
from .models import HumanAction, Project, RunLog
from .schemas import ActionComplete, ProjectCreate, ProjectPatch
from .seed import seed
from .vault import Credential, SocialAccount, Post
from .ops_routes import router as ops_router
from .postiz_routes import router as postiz_router
from .publisher_routes import router as publisher_router
from .email_routes import router as email_router
from .tradie_routes import router as tradie_router
from .backend_routes import router as backend_router
from .domain_routes import router as domain_router
from .mcp_routes import router as mcp_router
from .scheduler import start_scheduler, stop_scheduler

BASE = Path(__file__).resolve().parent
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with SessionLocal() as db:
        seed(db)
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="SteveJobless", version="0.2.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
app.include_router(ops_router)
app.include_router(postiz_router)
app.include_router(publisher_router)
app.include_router(email_router)
app.include_router(tradie_router)
app.include_router(backend_router)
app.include_router(domain_router)
app.include_router(mcp_router)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/", response_class=HTMLResponse)
def dashboard() -> HTMLResponse:
    return HTMLResponse((BASE / "templates" / "ops.html").read_text())


@app.get("/legacy", response_class=HTMLResponse)
def legacy_dashboard() -> HTMLResponse:
    return HTMLResponse((BASE / "templates" / "index.html").read_text())


@app.get("/desk", response_class=HTMLResponse)
def tradie_desk() -> HTMLResponse:
    return HTMLResponse((BASE / "templates" / "desk.html").read_text())


@app.get("/.well-known/agent-profile.json")
def agent_profile():
    """UCP-style profile so other agents (incl. Muse connectors) can consume us."""
    return {
        "name": "stevejobless-tradie",
        "version": "0.3.0",
        "transports": ["https"],
        "capabilities": ["jobs.intake", "jobs.quote", "jobs.schedule", "jobs.score", "email.observe"],
        "endpoints": {
            "intake": "/api/tradie/{slug}/intake",
            "slots": "/api/tradie/{slug}/slots",
            "quote": "/api/tradie/{slug}/jobs/{id}/quote",
            "confirm": "/api/tradie/{slug}/jobs/{id}/confirm",
            "observations": "/api/observations/email",
        },
        "auth": "bridge token (intake/observations) — contact operator",
    }


@app.get("/health")
def health():
    return {"ok": True, "service": "stevejobless"}


@app.get("/api/projects")
def list_projects(db: Session = Depends(get_db)):
    projects = db.scalars(select(Project).order_by(Project.id)).all()
    return [project_summary(p) for p in projects]


@app.post("/api/projects", status_code=201)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    if db.scalar(select(Project).where(Project.slug == payload.slug)):
        raise HTTPException(409, "slug already exists")
    p = Project(slug=payload.slug, name=payload.name, domain=payload.domain, passport=payload.passport)
    db.add(p); db.commit(); db.refresh(p)
    return project_summary(p)


@app.get("/api/projects/{slug}")
def get_project(slug: str, db: Session = Depends(get_db)):
    p = db.scalar(select(Project).where(Project.slug == slug))
    if not p: raise HTTPException(404, "project not found")
    return project_summary(p)


@app.patch("/api/projects/{slug}")
def patch_project(slug: str, payload: ProjectPatch, db: Session = Depends(get_db)):
    p = db.scalar(select(Project).where(Project.slug == slug))
    if not p: raise HTTPException(404, "project not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(p, key, value)
    db.commit(); db.refresh(p)
    return project_summary(p)


@app.post("/api/projects/{slug}/reconcile")
def reconcile(slug: str, db: Session = Depends(get_db)):
    p = db.scalar(select(Project).where(Project.slug == slug))
    if not p: raise HTTPException(404, "project not found")
    return reconcile_project(db, p)


@app.post("/api/reconcile")
def reconcile_everything(db: Session = Depends(get_db)):
    return reconcile_all(db)


@app.post("/api/autopilot")
def autopilot_everything(db: Session = Depends(get_db)):
    return run_autopilot_all(db)


@app.post("/api/projects/{slug}/autopilot")
def autopilot_project(slug: str, db: Session = Depends(get_db)):
    p = db.scalar(select(Project).where(Project.slug == slug))
    if not p: raise HTTPException(404, "project not found")
    return run_autopilot_project(db, p)


@app.patch("/api/actions/{action_id}")
def complete_action(action_id: int, payload: ActionComplete, db: Session = Depends(get_db)):
    action = db.get(HumanAction, action_id)
    if not action: raise HTTPException(404, "action not found")
    action.done = payload.done
    action.completed_at = datetime.now(timezone.utc) if payload.done else None
    db.commit()
    return {"ok": True, "id": action.id, "done": action.done}


@app.get("/api/runs")
def runs(limit: int = 20, db: Session = Depends(get_db)):
    rows = db.scalars(select(RunLog).order_by(RunLog.id.desc()).limit(min(limit, 100))).all()
    return [{"id": r.id, "project_id": r.project_id, "started_at": r.started_at, "finished_at": r.finished_at, "status": r.status, "summary": r.summary} for r in rows]
