"""Credential vault for storing API keys and tokens per business."""
from __future__ import annotations

import base64
import hashlib
import os
from pathlib import Path
from typing import Any

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Credential(Base):
    __tablename__ = "credentials"
    __table_args__ = (UniqueConstraint("business_slug", "platform", "key_name", name="uq_cred"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_slug: Mapped[str] = mapped_column(String(64), index=True)
    platform: Mapped[str] = mapped_column(String(64))
    key_name: Mapped[str] = mapped_column(String(128))
    value_encrypted: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SocialAccount(Base):
    __tablename__ = "social_accounts"
    __table_args__ = (UniqueConstraint("business_slug", "platform", name="uq_social"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_slug: Mapped[str] = mapped_column(String(64), index=True)
    platform: Mapped[str] = mapped_column(String(64))
    handle: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="connected")
    access_token_ref: Mapped[str | None] = mapped_column(String(256), nullable=True)
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_slug: Mapped[str] = mapped_column(String(64), index=True)
    platform: Mapped[str] = mapped_column(String(64))
    content: Mapped[str] = mapped_column(Text)
    media_urls: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    external_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


def _encrypt(value: str, key: str) -> str:
    """Simple XOR obfuscation. Not real encryption, but keeps values out of plain sight."""
    k = hashlib.sha256(key.encode()).digest()
    encrypted = bytes(b ^ k[i % len(k)] for i, b in enumerate(value.encode()))
    return base64.b64encode(encrypted).decode()


def _decrypt(encrypted: str, key: str) -> str:
    """Reverse XOR obfuscation."""
    k = hashlib.sha256(key.encode()).digest()
    data = base64.b64decode(encrypted)
    decrypted = bytes(b ^ k[i % len(k)] for i, b in enumerate(data))
    return decrypted.decode()


class CredentialVault:
    """Manages credentials for all businesses."""

    def __init__(self, db_session, master_key: str | None = None):
        self.db = db_session
        self.master_key = master_key or os.getenv("STEVE_MASTER_KEY", "stevejobless-default-key")

    def set_credential(self, business_slug: str, platform: str, key_name: str, value: str) -> None:
        existing = self.db.query(Credential).filter_by(
            business_slug=business_slug, platform=platform, key_name=key_name
        ).first()
        if existing:
            existing.value_encrypted = _encrypt(value, self.master_key)
        else:
            cred = Credential(
                business_slug=business_slug,
                platform=platform,
                key_name=key_name,
                value_encrypted=_encrypt(value, self.master_key),
            )
            self.db.add(cred)
        self.db.commit()

    def get_credential(self, business_slug: str, platform: str, key_name: str) -> str | None:
        cred = self.db.query(Credential).filter_by(
            business_slug=business_slug, platform=platform, key_name=key_name
        ).first()
        if not cred:
            return None
        return _decrypt(cred.value_encrypted, self.master_key)

    def list_credentials(self, business_slug: str) -> list[dict]:
        creds = self.db.query(Credential).filter_by(business_slug=business_slug).all()
        return [{"platform": c.platform, "key_name": c.key_name, "created_at": c.created_at.isoformat()} for c in creds]

    def delete_credential(self, business_slug: str, platform: str, key_name: str) -> bool:
        cred = self.db.query(Credential).filter_by(
            business_slug=business_slug, platform=platform, key_name=key_name
        ).first()
        if cred:
            self.db.delete(cred)
            self.db.commit()
            return True
        return False


class SocialManager:
    """Manages social account connections per business."""

    def __init__(self, db_session):
        self.db = db_session

    def connect(self, business_slug: str, platform: str, handle: str | None = None) -> SocialAccount:
        existing = self.db.query(SocialAccount).filter_by(
            business_slug=business_slug, platform=platform
        ).first()
        if existing:
            existing.handle = handle or existing.handle
            existing.status = "connected"
            self.db.commit()
            return existing
        account = SocialAccount(
            business_slug=business_slug, platform=platform, handle=handle, status="connected"
        )
        self.db.add(account)
        self.db.commit()
        return account

    def disconnect(self, business_slug: str, platform: str) -> bool:
        account = self.db.query(SocialAccount).filter_by(
            business_slug=business_slug, platform=platform
        ).first()
        if account:
            self.db.delete(account)
            self.db.commit()
            return True
        return False

    def list_accounts(self, business_slug: str) -> list[dict]:
        accounts = self.db.query(SocialAccount).filter_by(business_slug=business_slug).all()
        return [{"platform": a.platform, "handle": a.handle, "status": a.status} for a in accounts]


class PostManager:
    """Manages posts per business."""

    def __init__(self, db_session):
        self.db = db_session

    def create_post(self, business_slug: str, platform: str, content: str,
                    media_urls: list[str] | None = None, scheduled_at: datetime | None = None) -> Post:
        post = Post(
            business_slug=business_slug,
            platform=platform,
            content=content,
            media_urls=",".join(media_urls) if media_urls else None,
            scheduled_at=scheduled_at,
            status="scheduled" if scheduled_at else "draft",
        )
        self.db.add(post)
        self.db.commit()
        return post

    def list_posts(self, business_slug: str, limit: int = 20) -> list[dict]:
        posts = self.db.query(Post).filter_by(business_slug=business_slug).order_by(Post.created_at.desc()).limit(limit).all()
        return [{
            "id": p.id, "platform": p.platform, "content": p.content[:100],
            "status": p.status, "scheduled_at": p.scheduled_at.isoformat() if p.scheduled_at else None,
            "posted_at": p.posted_at.isoformat() if p.posted_at else None,
        } for p in posts]

    def get_pending_posts(self) -> list[Post]:
        return self.db.query(Post).filter(
            Post.status == "scheduled",
            Post.scheduled_at <= datetime.now(timezone.utc),
        ).all()
