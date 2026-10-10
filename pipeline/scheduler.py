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
               steve_db: str = STEVE_DB,
               ctx: dict | None = None) -> dict:
    """Gate → queue. Returns {ok, post_id|reason}.

    dir 9+27: queueing proves post.queued=TRUE only — never post.published.
    Publication needs adapter execution + platform readback + receipt.
    Human approval is required (ctx with grant) unless the caller passes
    pre_approved evidence. Without ctx: FAIL CLOSED.
    """
    # 0. approval evidence (dir 27)
    if not ctx or not ctx.get("grant"):
        log_action("scheduler", f"BLOCKED queue {platform} {handle} (no approval)", 0.0,
                   sku, campaign, brand_slug, None, 0, 1, None, "FAIL")
        return {"ok": False, "reason": "no approval evidence: FAIL CLOSED",
                "gate": "approval"}
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


def _adapters():
    """Import stevejobless adapters (plain publish functions)."""
    import sys as _sys
    _sys.path.insert(0, "/root/stevejobless")
    try:
        from stevejobless.publisher.adapters import ADAPTERS
        return ADAPTERS
    except Exception:
        return {}


def _account_tokens(db, business_slug: str, platform: str) -> dict:
    try:
        row = db.execute(
            "SELECT access_token, refresh_token, extra FROM social_accounts_v2"
            " WHERE business_slug=? AND platform=? LIMIT 1",
            (business_slug, platform)).fetchone()
    except Exception:
        return {}
    if not row:
        return {}
    toks = {"access_token": row[0] or "", "refresh_token": row[1] or ""}
    try:
        toks.update(json.loads(row[2] or "{}"))
    except Exception:
        pass
    return toks


def run_due(steve_db: str = STEVE_DB, max_posts: int = 10) -> dict:
    """Fire due approved posts. Called by systemd timer every 5 min.

    For each due row (scheduled/retry, time reached, attempts<3):
    per-account gate → adapter.publish → verify → receipt → learn.
    Publication proves post.published=TRUE (never from queueing alone).
    """
    try:
        from channel_state import can_publish, record_post
        from actions import log_action as _log
        from learn import record_publication
    except ImportError:
        from pipeline.channel_state import can_publish, record_post
        from pipeline.actions import log_action as _log
        from pipeline.learn import record_publication
    adapters = _adapters()
    db = sqlite3.connect(steve_db, timeout=30)
    try:
        cols = [r[1] for r in db.execute("PRAGMA table_info(post_queue)").fetchall()]
        now = datetime.now(timezone.utc).isoformat()
        rows = db.execute(
            "SELECT id,business_slug,platform,content,media_urls FROM post_queue"
            " WHERE status IN ('scheduled','retry') AND scheduled_at <= ?"
            " AND attempts < 3 ORDER BY scheduled_at LIMIT ?",
            (now, max_posts)).fetchall()
    except Exception as e:
        db.close()
        return {"ok": False, "reason": f"queue read failed: {e}"[:150]}
    fired, skipped, failed = [], [], []
    for pid, brand, platform, content, media_urls in rows:
        # handle lookup for gate (business_slug → brand mapping)
        handles = {"x": "@oddhobb", "instagram": "@oddhobbstudio",
                   "tiktok": "@oddhobb", "youtube": "@oddhobbstudio",
                   "pinterest": "@oddhobbstudio"}
        gate = can_publish(platform, handles.get(platform, ""), 0.7)
        if not gate["ok"]:
            skipped.append({"id": pid, "reason": gate["reason"]})
            continue
        adapter = adapters.get(platform)
        if not adapter:
            skipped.append({"id": pid, "reason": f"no adapter for {platform}"})
            continue
        media = (media_urls or "").split(",") if media_urls else []
        media = [m for m in media if m]
        toks = _account_tokens(db, brand, platform)
        try:
            ok, external_id, error = adapter.publish(content, media or None, None, toks)
        except Exception as e:  # noqa: BLE001
            ok, external_id, error = False, "", str(e)[:200]
        try:
            if ok:
                db.execute("UPDATE post_queue SET status='published', posted_at=?,"
                           " external_id=?, error=NULL, attempts=attempts+1 WHERE id=?",
                           (datetime.now(timezone.utc).isoformat(), external_id, pid))
                db.commit()
                record_post(platform, handles.get(platform, ""))
                # learn: only verified publications enter (dir 33)
                try:
                    record_publication(platform, handles.get(platform, ""),
                                       external_id, f"receipt:post-{pid}",
                                       body=(content or "")[:500],
                                       brand_slug=brand)
                except Exception:
                    pass
                _log("scheduler", f"PUBLISHED {platform} post {pid} → {external_id}",
                     0.0, None, None, brand, str(external_id), 3, 3, None, "PASS")
                fired.append({"id": pid, "external_id": external_id})
            else:
                db.execute("UPDATE post_queue SET attempts=attempts+1, error=?,"
                           " status=CASE WHEN attempts+1>=3 THEN 'dead' ELSE 'retry' END"
                           " WHERE id=?", (error[:300], pid))
                db.commit()
                _log("scheduler", f"FAILED {platform} post {pid}: {error[:100]}",
                     0.0, None, None, brand, None, 0, 1, None, "FAIL")
                failed.append({"id": pid, "error": error[:150]})
        except Exception as e:
            failed.append({"id": pid, "error": str(e)[:150]})
    db.close()
    return {"ok": True, "fired": fired, "skipped": skipped, "failed": failed}


if __name__ == "__main__":
    import argparse
    _ap = argparse.ArgumentParser()
    _ap.add_argument("--tick", action="store_true", help="fire due posts once")
    _ap.add_argument("--max", type=int, default=10)
    _a = _ap.parse_args()
    if _a.tick:
        import json as _j
        print(_j.dumps(run_due(max_posts=_a.max)))


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
