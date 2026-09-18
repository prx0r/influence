"""Postiz social scheduling routes."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .config import settings
from .postiz import PostizPublisher

router = APIRouter(prefix="/api/postiz", tags=["postiz"])


def _publisher() -> PostizPublisher:
    if not settings.postiz_url or not settings.postiz_api_key:
        raise HTTPException(
            503,
            "Postiz not configured. Set POSTIZ_URL and POSTIZ_API_KEY env vars.",
        )
    return PostizPublisher(settings.postiz_url, settings.postiz_api_key)


# --- Request schemas ---

class PostCreate(BaseModel):
    integration_id: str
    content: str
    post_type: str = "schedule"
    date: str | None = None
    images: list[dict[str, str]] | None = None
    settings: dict[str, Any] | None = None
    tags: list[str] | None = None
    short_link: bool = False


class PostSchedule(BaseModel):
    integration_id: str
    content: str
    date: str
    images: list[dict[str, str]] | None = None
    settings: dict[str, Any] | None = None


# --- Health ---

@router.get("/health")
def postiz_health():
    pub = _publisher()
    ok = pub.health_check()
    return {"ok": ok, "postiz_url": settings.postiz_url}


# --- Integrations ---

@router.get("/integrations")
def list_integrations(group: str | None = None):
    pub = _publisher()
    return pub.list_integrations(group)


# --- Posts ---

@router.post("/posts", status_code=201)
def create_post(payload: PostCreate):
    pub = _publisher()
    return pub.create_post(
        payload.integration_id,
        payload.content,
        post_type=payload.post_type,
        date=payload.date,
        images=payload.images,
        settings=payload.settings,
        tags=payload.tags,
        short_link=payload.short_link,
    )


@router.post("/posts/now", status_code=201)
def post_now(payload: PostCreate):
    pub = _publisher()
    return pub.post_now(
        payload.integration_id,
        payload.content,
        images=payload.images,
        settings=payload.settings,
    )


@router.post("/posts/schedule", status_code=201)
def schedule_post(payload: PostSchedule):
    pub = _publisher()
    return pub.schedule_post(
        payload.integration_id,
        payload.content,
        payload.date,
        images=payload.images,
        settings=payload.settings,
    )


@router.get("/posts")
def list_posts(start_date: str, end_date: str, customer: str | None = None):
    pub = _publisher()
    return pub.list_posts(start_date, end_date, customer)


@router.delete("/posts/{post_id}")
def delete_post(post_id: str):
    pub = _publisher()
    return pub.delete_post(post_id)


# --- Analytics ---

@router.get("/analytics/{integration_id}")
def get_analytics(integration_id: str, date: str | None = None):
    pub = _publisher()
    return pub.get_integration_analytics(integration_id, date)


@router.get("/analytics/post/{post_id}")
def get_post_analytics(post_id: str, date: str | None = None):
    pub = _publisher()
    return pub.get_post_analytics(post_id, date)


# --- Uploads ---

@router.post("/upload")
def upload_media(file_path: str):
    pub = _publisher()
    return pub.upload_media(file_path)


# --- Groups ---

@router.get("/groups")
def list_groups():
    pub = _publisher()
    return pub.list_groups()
