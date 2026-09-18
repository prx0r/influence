"""Background scheduler — fires due posts."""
from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime, timezone

from sqlalchemy import select

from .db import SessionLocal
from .publisher.adapters import ADAPTERS
from .publisher.models import PostQueue, SocialAccount

log = logging.getLogger("stevejobless.scheduler")

_running = False
_thread: threading.Thread | None = None


def _get_account_tokens(db, business_slug: str, platform: str) -> dict:
    account = db.scalar(
        select(SocialAccount).where(
            SocialAccount.business_slug == business_slug,
            SocialAccount.platform == platform,
        )
    )
    if not account:
        return {}
    extra = json.loads(account.extra) if account.extra else {}
    tokens = {
        "access_token": account.access_token or "",
        **extra,
    }
    return tokens


def _process_post(db, post: PostQueue) -> None:
    adapter = ADAPTERS.get(post.platform)
    if not adapter:
        post.status = "failed"
        post.error = f"no adapter for platform: {post.platform}"
        return

    tokens = _get_account_tokens(db, post.business_slug, post.platform)
    media_urls = post.media_urls.split(",") if post.media_urls else None
    settings = json.loads(post.platform_settings) if post.platform_settings else None

    ok, post_id, error = adapter.publish(post.content, media_urls, settings, tokens)

    post.attempts += 1
    if ok:
        post.status = "published"
        post.posted_at = datetime.now(timezone.utc)
        post.external_id = post_id
        post.error = None
    else:
        post.error = error
        if post.attempts >= 3:
            post.status = "dead"
        else:
            post.status = "retry"


def _tick() -> None:
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        due = db.scalars(
            select(PostQueue).where(
                PostQueue.status.in_(["scheduled", "retry"]),
                PostQueue.scheduled_at <= now,
            )
        ).all()

        for post in due:
            post.status = "publishing"
            db.commit()
            try:
                _process_post(db, post)
            except Exception as e:
                post.status = "failed" if post.attempts >= 3 else "retry"
                post.error = str(e)[:500]
            db.commit()

        drafts = db.scalars(
            select(PostQueue).where(PostQueue.status == "now")
        ).all()
        for post in drafts:
            post.status = "publishing"
            post.scheduled_at = now
            db.commit()
            try:
                _process_post(db, post)
            except Exception as e:
                post.status = "failed" if post.attempts >= 3 else "retry"
                post.error = str(e)[:500]
            db.commit()


def _loop() -> None:
    global _running
    while _running:
        try:
            _tick()
        except Exception as e:
            log.error("scheduler tick error: %s", e)
        time.sleep(15)


def start_scheduler() -> None:
    global _running, _thread
    if _running:
        return
    _running = True
    _thread = threading.Thread(target=_loop, daemon=True, name="post-scheduler")
    _thread.start()
    log.info("post scheduler started")


def stop_scheduler() -> None:
    global _running
    _running = False
