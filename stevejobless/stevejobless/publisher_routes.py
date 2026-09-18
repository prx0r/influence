"""Publisher API routes."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import SessionLocal
from .publisher.adapters import ADAPTERS
from .publisher.models import PostQueue, SocialAccount

router = APIRouter(prefix="/api/publisher", tags=["publisher"])


def _get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- Schemas ---

class PostCreate(BaseModel):
    business_slug: str
    platform: str
    content: str
    media_urls: list[str] | None = None
    settings: dict[str, Any] | None = None
    scheduled_at: str | None = None


class AccountConnect(BaseModel):
    business_slug: str
    platform: str
    provider_account_id: str
    display_name: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    extra: dict[str, Any] | None = None


# --- Posts ---

@router.get("/posts")
def list_posts(business_slug: str | None = None, status: str | None = None,
               limit: int = 50, db: Session = Depends(_get_db)):
    q = select(PostQueue).order_by(PostQueue.id.desc())
    if business_slug:
        q = q.where(PostQueue.business_slug == business_slug)
    if status:
        q = q.where(PostQueue.status == status)
    rows = db.scalars(q.limit(min(limit, 200))).all()
    return [_post_dict(p) for p in rows]


@router.post("/posts", status_code=201)
def create_post(payload: PostCreate, db: Session = Depends(_get_db)):
    if payload.platform not in ADAPTERS:
        raise HTTPException(400, f"unknown platform: {payload.platform}")

    scheduled = datetime.fromisoformat(payload.scheduled_at) if payload.scheduled_at else None
    status = "scheduled" if scheduled else "draft"

    post = PostQueue(
        business_slug=payload.business_slug,
        platform=payload.platform,
        content=payload.content,
        media_urls=",".join(payload.media_urls) if payload.media_urls else None,
        platform_settings=json.dumps(payload.settings) if payload.settings else None,
        scheduled_at=scheduled,
        status=status,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return _post_dict(post)


@router.post("/posts/{post_id}/publish")
def publish_now(post_id: int, db: Session = Depends(_get_db)):
    post = db.get(PostQueue, post_id)
    if not post:
        raise HTTPException(404, "post not found")

    adapter = ADAPTERS.get(post.platform)
    if not adapter:
        raise HTTPException(400, f"no adapter for: {post.platform}")

    from .scheduler import _get_account_tokens, _process_post
    post.status = "publishing"
    db.commit()
    _process_post(db, post)
    db.commit()
    return _post_dict(post)


@router.delete("/posts/{post_id}")
def delete_post(post_id: int, db: Session = Depends(_get_db)):
    post = db.get(PostQueue, post_id)
    if not post:
        raise HTTPException(404, "post not found")
    if post.status in ("publishing", "published"):
        raise HTTPException(400, "cannot delete publishing/published post")
    db.delete(post)
    db.commit()
    return {"ok": True}


# --- Accounts ---

@router.get("/accounts")
def list_accounts(business_slug: str | None = None, db: Session = Depends(_get_db)):
    q = select(SocialAccount).order_by(SocialAccount.id)
    if business_slug:
        q = q.where(SocialAccount.business_slug == business_slug)
    rows = db.scalars(q).all()
    return [_account_dict(a) for a in rows]


@router.post("/accounts", status_code=201)
def connect_account(payload: AccountConnect, db: Session = Depends(_get_db)):
    existing = db.scalar(
        select(SocialAccount).where(
            SocialAccount.business_slug == payload.business_slug,
            SocialAccount.platform == payload.platform,
            SocialAccount.provider_account_id == payload.provider_account_id,
        )
    )
    if existing:
        existing.display_name = payload.display_name or existing.display_name
        existing.access_token = payload.access_token or existing.access_token
        existing.refresh_token = payload.refresh_token or existing.refresh_token
        existing.extra = json.dumps(payload.extra) if payload.extra else existing.extra
        db.commit()
        return _account_dict(existing)

    account = SocialAccount(
        business_slug=payload.business_slug,
        platform=payload.platform,
        provider_account_id=payload.provider_account_id,
        display_name=payload.display_name,
        access_token=payload.access_token,
        refresh_token=payload.refresh_token,
        extra=json.dumps(payload.extra) if payload.extra else None,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return _account_dict(account)


@router.delete("/accounts/{account_id}")
def disconnect_account(account_id: int, db: Session = Depends(_get_db)):
    account = db.get(SocialAccount, account_id)
    if not account:
        raise HTTPException(404, "account not found")
    db.delete(account)
    db.commit()
    return {"ok": True}


# --- Platforms ---

@router.get("/platforms")
def list_platforms():
    return [{"id": k, "name": k.title()} for k in ADAPTERS]


# --- Helpers ---

def _post_dict(p: PostQueue) -> dict:
    return {
        "id": p.id,
        "business_slug": p.business_slug,
        "platform": p.platform,
        "content": p.content[:200],
        "status": p.status,
        "scheduled_at": p.scheduled_at.isoformat() if p.scheduled_at else None,
        "posted_at": p.posted_at.isoformat() if p.posted_at else None,
        "external_id": p.external_id,
        "error": p.error,
        "attempts": p.attempts,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


def _account_dict(a: SocialAccount) -> dict:
    return {
        "id": a.id,
        "business_slug": a.business_slug,
        "platform": a.platform,
        "provider_account_id": a.provider_account_id,
        "display_name": a.display_name,
        "connected_at": a.connected_at.isoformat() if a.connected_at else None,
    }
