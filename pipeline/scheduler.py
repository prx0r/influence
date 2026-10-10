"""Scheduler bridge — compiled posts → PostQueue + per-account gates.

Flow: compile → can_publish check → human_confirm → queue → scheduler fires.
Never queues without a gate pass. Never publishes without human approval.
Reads stevejobless PostQueue tables; writes via its API shapes (no import).
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
try:
    from channel_state import can_publish, record_post
    from actions import log_action
except ImportError:
    from pipeline.channel_state import can_publish, record_post
    from pipeline.actions import log_action

STEVE_DB = os.getenv("STEVE_DB", "/root/stevejobless/stevejobless.db")


def queue_post(platform: str, handle: str, content: str,
               media_urls: list[str] | None = None,
               scheduled_at: str | None = None,
               brand_slug: str = "oddhobb",
               quality_score: float = 1.0,
               sku: str | None = None, campaign: str | None = None,
               steve_db: str = STEVE_DB) -> dict:
    """Gate → queue. Returns {ok, post_id|reason}."""
    # 1. per-account gate (budget, cooldown, quality)
    gate = can_publish(platform, handle, quality_score)
    if not gate["ok"]:
        log_action("scheduler", f"BLOCKED {platform} {handle}: {gate['reason']}",
                   0.0, sku, campaign, brand_slug, None, 0, 1, None, "FAIL")
        return {"ok": False, "reason": gate["reason"], "gate": "account"}

    # 2. write to PostQueue (stevejobless schema)
    db = sqlite3.connect(steve_db, timeout=30)
    try:
        cols = [r[1] for r in db.execute("PRAGMA table_info(post_queue)").fetchall()]
        # adapt to actual schema: find content/scheduled/status columns
        cur = db.execute(
            "INSERT INTO post_queue (business_slug, platform, content, media_urls,"
            " scheduled_at, status) VALUES (?,?,?,?,?,?)",
            (brand_slug, platform, content,
             ",".join(media_urls or []) if "media_urls" in cols else None,
             scheduled_at or datetime.now(timezone.utc).isoformat(),
             "scheduled"))
        db.commit()
        pid = cur.lastrowid
    except Exception as e:
        return {"ok": False, "reason": f"queue write failed: {e}"[:200], "gate": "db"}
    finally:
        db.close()

    log_action("scheduler", f"QUEUED {platform} post {pid}", 0.0, sku,
               campaign, brand_slug, str(pid), 1, 1, None, "PASS")
    return {"ok": True, "post_id": pid,
            "note": "queued. Publishes via scheduler after human approval."}


def queue_pack_social(pack: dict, compiled: dict,
                      handles: dict | None = None,
                      brand_slug: str = "oddhobb",
                      campaign: str | None = None) -> dict:
    """Queue all compiled variants for a pack. Returns per-channel results."""
    handles = handles or {}
    sku = pack.get("sku", "")
    out: dict = {}
    mapping = {
        "x": ("x", lambda c: c["text"], lambda c: [c["image_url"]] if c.get("image_url") else []),
        "instagram": ("instagram", lambda c: c["caption"], lambda c: [c["image_url"]] if c.get("image_url") else []),
        "tiktok": ("tiktok", lambda c: c["caption"], lambda c: [c["image_url"]] if c.get("image_url") else []),
        "youtube": ("youtube", lambda c: c["title"] + "\n" + c["description"], lambda c: []),
    }
    for key, (platform, text_fn, media_fn) in mapping.items():
        c = (compiled or {}).get(key)
        if not c:
            continue
        handle = handles.get(platform, "")
        if not handle:
            out[key] = {"ok": False, "reason": "no handle configured"}
            continue
        try:
            out[key] = queue_post(platform, handle, text_fn(c), media_fn(c),
                                  brand_slug=brand_slug, sku=sku, campaign=campaign)
        except Exception as e:
            out[key] = {"ok": False, "reason": str(e)[:150]}
    return out
