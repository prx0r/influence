"""Business Operations API routes."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import SessionLocal
from .models import Project
from .vault import CredentialVault, PostManager, SocialManager

router = APIRouter(prefix="/api/ops", tags=["operations"])


def _get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- Request schemas ---

class BusinessCreate(BaseModel):
    slug: str
    name: str
    domain: str | None = None
    passport: dict[str, Any] = {}


class CredentialSet(BaseModel):
    platform: str
    key_name: str
    value: str


class SocialConnect(BaseModel):
    platform: str
    handle: str | None = None


class PostCreate(BaseModel):
    platform: str
    content: str
    media_urls: list[str] | None = None
    scheduled_at: str | None = None


# --- Business CRUD ---

@router.get("/businesses")
def list_businesses(db: Session = Depends(_get_db)):
    projects = db.scalars(select(Project).order_by(Project.id)).all()
    return [_business_summary(p, db) for p in projects]


@router.post("/businesses", status_code=201)
def create_business(payload: BusinessCreate, db: Session = Depends(_get_db)):
    if db.scalar(select(Project).where(Project.slug == payload.slug)):
        raise HTTPException(409, "slug already exists")
    p = Project(slug=payload.slug, name=payload.name, domain=payload.domain, passport=payload.passport)
    db.add(p)
    db.commit()
    db.refresh(p)
    return _business_summary(p, db)


@router.get("/businesses/{slug}")
def get_business(slug: str, db: Session = Depends(_get_db)):
    p = db.scalar(select(Project).where(Project.slug == slug))
    if not p:
        raise HTTPException(404, "business not found")
    return _business_summary(p, db)


@router.patch("/businesses/{slug}")
def update_business(slug: str, payload: BusinessCreate, db: Session = Depends(_get_db)):
    p = db.scalar(select(Project).where(Project.slug == slug))
    if not p:
        raise HTTPException(404, "business not found")
    if payload.name:
        p.name = payload.name
    if payload.domain is not None:
        p.domain = payload.domain
    if payload.passport:
        p.passport = payload.passport
    db.commit()
    db.refresh(p)
    return _business_summary(p, db)


@router.delete("/businesses/{slug}")
def delete_business(slug: str, db: Session = Depends(_get_db)):
    p = db.scalar(select(Project).where(Project.slug == slug))
    if not p:
        raise HTTPException(404, "business not found")
    db.delete(p)
    db.commit()
    return {"ok": True}


# --- Credentials ---

@router.get("/businesses/{slug}/credentials")
def list_credentials(slug: str, db: Session = Depends(_get_db)):
    vault = CredentialVault(db)
    return vault.list_credentials(slug)


@router.post("/businesses/{slug}/credentials", status_code=201)
def set_credential(slug: str, payload: CredentialSet, db: Session = Depends(_get_db)):
    vault = CredentialVault(db)
    vault.set_credential(slug, payload.platform, payload.key_name, payload.value)
    return {"ok": True, "platform": payload.platform, "key_name": payload.key_name}


@router.delete("/businesses/{slug}/credentials/{platform}/{key_name}")
def delete_credential(slug: str, platform: str, key_name: str, db: Session = Depends(_get_db)):
    vault = CredentialVault(db)
    deleted = vault.delete_credential(slug, platform, key_name)
    if not deleted:
        raise HTTPException(404, "credential not found")
    return {"ok": True}


# --- Social Accounts ---

@router.get("/businesses/{slug}/social")
def list_social(slug: str, db: Session = Depends(_get_db)):
    mgr = SocialManager(db)
    return mgr.list_accounts(slug)


@router.post("/businesses/{slug}/social", status_code=201)
def connect_social(slug: str, payload: SocialConnect, db: Session = Depends(_get_db)):
    mgr = SocialManager(db)
    account = mgr.connect(slug, payload.platform, payload.handle)
    return {"ok": True, "platform": account.platform, "handle": account.handle}


@router.delete("/businesses/{slug}/social/{platform}")
def disconnect_social(slug: str, platform: str, db: Session = Depends(_get_db)):
    mgr = SocialManager(db)
    deleted = mgr.disconnect(slug, platform)
    if not deleted:
        raise HTTPException(404, "social account not found")
    return {"ok": True}


# --- Posts ---

@router.get("/businesses/{slug}/posts")
def list_posts(slug: str, limit: int = 20, db: Session = Depends(_get_db)):
    mgr = PostManager(db)
    return mgr.list_posts(slug, limit)


@router.post("/businesses/{slug}/posts", status_code=201)
def create_post(slug: str, payload: PostCreate, db: Session = Depends(_get_db)):
    mgr = PostManager(db)
    scheduled = datetime.fromisoformat(payload.scheduled_at) if payload.scheduled_at else None
    post = mgr.create_post(slug, payload.platform, payload.content, payload.media_urls, scheduled)
    return {"ok": True, "id": post.id, "status": post.status}


# --- Dashboard Summary ---

@router.get("/dashboard")
def dashboard_summary(db: Session = Depends(_get_db)):
    projects = db.scalars(select(Project).order_by(Project.id)).all()
    businesses = []
    total_actions = 0
    for p in projects:
        summary = _business_summary(p, db)
        businesses.append(summary)
        total_actions += len(summary.get("pending_actions", []))
    return {
        "total_businesses": len(businesses),
        "total_pending_actions": total_actions,
        "businesses": businesses,
    }


# --- Helpers ---

def _business_summary(project: Project, db: Session) -> dict:
    from .engine import project_summary

    summary = project_summary(project)
    social_mgr = SocialManager(db)
    social = social_mgr.list_accounts(project.slug)

    return {
        "slug": project.slug,
        "name": project.name,
        "domain": project.domain,
        "progress": summary["progress"],
        "resources": summary["resources"],
        "pending_actions": summary["actions"],
        "social_accounts": social,
    }
