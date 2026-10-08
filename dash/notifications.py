"""Unified notifications + agent feed for the influence dash.

Cross-channel: phone SMS + cmail email + local run/receipt/journal events.
Stdlib + urllib only. Failures degrade to empty slices — never crash the dash.
"""
from __future__ import annotations

import json
import os
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

ROOT = os.path.dirname(os.path.abspath(__file__))
INFLUENCE = os.path.dirname(ROOT)
PHONE_CANDIDATES = [
    os.environ.get("PHONE_WORKER_URL", "").rstrip("/"),
    "https://phone.agentcom.org",
    "https://oddhobb-phone.tradesprior.workers.dev",
    "http://127.0.0.1:8794",
]
CMAIL = os.environ.get("CMAIL_URL", "https://cmail.tradesprior.workers.dev").rstrip("/")
BRAND_MAILBOXES = os.environ.get(
    "BRAND_MAILBOXES",
    "hello@oddhobb.com,orders@oddhobb.com,support@oddhobb.com,hello@pogtown.com",
).split(",")
DB_PATH = os.getenv("DASH_DB", os.path.join(ROOT, "influence.db"))
JOURNAL_PATH = os.getenv("DASH_JOURNAL", os.path.join(ROOT, "decisions.db"))
RECEIPT_LOG = os.getenv("RECEIPT_LOG", os.path.join(ROOT, "receipts.jsonl"))


def _http_json(url: str, timeout: float = 8.0, headers: dict | None = None,
               data: bytes | None = None, method: str | None = None) -> Any:
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"User-Agent": "influence-dash/0.5", **(headers or {})},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read() or b"null")


def _phone_auth() -> str:
    for path in (
        os.environ.get("PHONE_AUTH_FILE", ""),
        os.path.expanduser("~/stevejobless/.phone_auth"),
        os.path.expanduser("~/.phone_auth"),
    ):
        if path and os.path.exists(path):
            try:
                return open(path).read().strip()
            except OSError:
                pass
    return ""


def fetch_sms(limit: int = 15) -> list[dict]:
    auth = _phone_auth()
    headers = {"Authorization": f"Bearer {auth}"} if auth else {}
    last = None
    for base in PHONE_CANDIDATES:
        if not base:
            continue
        try:
            data = _http_json(base + "/v1/inbox?kind=sms", headers=headers)
            events = data.get("events") or []
            return events[:limit]
        except Exception as e:
            last = e
            continue
    return []


def fetch_email(limit: int = 20) -> list[dict]:
    out: list[dict] = []
    for mbox in BRAND_MAILBOXES:
        mbox = mbox.strip()
        if not mbox:
            continue
        try:
            body = json.dumps({"tool": "email.inbox", "args": {"mailbox": mbox}, "actor": "owner"}).encode()
            data = _http_json(
                CMAIL + "/mcp", headers={"Content-Type": "application/json"},
                data=body, method="POST",
            )
            msgs = data.get("messages") or []
            for m in msgs:
                m = dict(m)
                m["_mailbox"] = mbox
                out.append(m)
        except Exception:
            continue
    # newest first by received_at when present
    def _key(m: dict):
        return str(m.get("received_at") or m.get("at") or "")
    out.sort(key=_key, reverse=True)
    return out[:limit]


def _local_events(limit: int = 20) -> tuple[list[dict], list[dict]]:
    runs: list[dict] = []
    receipts: list[dict] = []
    try:
        db = sqlite3.connect(DB_PATH)
        try:
            rows = db.execute(
                "SELECT id, status, summary, started_at FROM run_logs "
                "ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            for rid, status, summary, started in rows:
                try:
                    s = json.loads(summary) if summary else {}
                except Exception:
                    s = {"raw": str(summary)[:200]}
                counts = s.get("counts") if isinstance(s, dict) else {}
                runs.append({
                    "id": f"run-{rid}",
                    "kind": "run",
                    "source": "influence",
                    "title": f"Reconcile {status}",
                    "body": f"{counts} · {s.get('progress', '?')}%" if counts else str(s)[:160],
                    "at": str(started or ""),
                    "ok": str(status).upper() in {"OK", "RUNNING", "DONE"},
                    "ref": str(rid),
                })
        finally:
            db.close()
    except Exception:
        pass
    try:
        if os.path.exists(RECEIPT_LOG):
            with open(RECEIPT_LOG, encoding="utf-8", errors="replace") as f:
                lines = f.readlines()[-limit:]
            for line in reversed(lines):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                payload = entry.get("payload", entry)
                rc = payload.get("receipt", {})
                gates = rc.get("gates") or []
                failed = [g.get("id") for g in gates if g.get("result") not in (None, "PASS", "pass", True)]
                receipts.append({
                    "id": rc.get("id") or "receipt",
                    "kind": "receipt",
                    "source": "qp",
                    "title": "Receipt " + ("PASS" if rc.get("passed") else "FAIL"),
                    "body": (
                        f"gates {len(gates)}"
                        + (f" failed={failed[:3]}" if failed else "")
                        + f" · proof {rc.get('proof_level', '?')}"
                    ),
                    "at": str(entry.get("at") or entry.get("ts") or ""),
                    "ok": bool(rc.get("passed")),
                    "ref": rc.get("id"),
                })
    except Exception:
        pass
    return runs, receipts


def _journal_events(limit: int = 15) -> list[dict]:
    out: list[dict] = []
    try:
        db = sqlite3.connect(JOURNAL_PATH)
        try:
            try:
                rows = db.execute(
                    "SELECT ref, task_id, at, used FROM predictions ORDER BY at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
                for ref, task_id, at, used in rows:
                    out.append({
                        "id": f"pred-{ref}",
                        "kind": "prediction",
                        "source": "hloop",
                        "title": "Prediction " + ("used" if used else "banked"),
                        "body": f"task {task_id}",
                        "at": str(datetime.fromtimestamp(int(at), tz=timezone.utc).isoformat()) if at else "",
                        "ok": True,
                        "ref": ref,
                    })
            except sqlite3.Error:
                pass
            try:
                rows = db.execute(
                    "SELECT idem, action, state, updated_at FROM effects "
                    "ORDER BY updated_at DESC LIMIT ?", (limit,)
                ).fetchall()
                for idem, action, state, updated in rows:
                    out.append({
                        "id": f"fx-{idem}",
                        "kind": "effect",
                        "source": "journal",
                        "title": f"Journal {state}",
                        "body": f"{action} · {idem}",
                        "at": str(updated or ""),
                        "ok": str(state).upper() in {"AUTHORIZED", "PROVEN", "DONE", "APPROVED_PENDING_QP"},
                        "ref": idem,
                    })
            except sqlite3.Error:
                pass
        finally:
            db.close()
    except Exception:
        pass
    return out


def _extract_otp(text: str) -> str | None:
    import re
    cands = []
    for m in re.finditer(r"\b(\d{4,8})\b", text or ""):
        v = m.group(1)
        if len(v) == 4 and 1990 <= int(v) <= 2100:
            continue  # skip years
        if set(v) == {"0"}:
            continue  # skip zero runs
        cands.append(v)
    cands.sort(key=lambda v: (0 if len(v) == 6 else 1, -len(v)))
    return cands[0] if cands else None


_KIND_PRI = {"receipt": 0, "run": 1, "effect": 2, "prediction": 3, "task": 4, "sms": 5, "email": 6}


def _sort_feed(items: list[dict], limit: int) -> list[dict]:
    """Round-robin by kind so one source cannot flood the feed."""
    from itertools import groupby
    by_kind: dict[str, list[dict]] = {}
    for n in items:
        by_kind.setdefault(n.get("kind") or "other", []).append(n)
    for kind in by_kind:
        by_kind[kind].sort(key=lambda n: str(n.get("at") or ""), reverse=True)
    order = ["receipt", "run", "task", "effect", "prediction", "sms", "email", "other"]
    kinds = [k for k in order if k in by_kind] + [k for k in by_kind if k not in order]
    out: list[dict] = []
    i = 0
    while len(out) < limit:
        added = False
        for k in kinds:
            if i < len(by_kind[k]):
                out.append(by_kind[k][i])
                added = True
                if len(out) >= limit:
                    break
        if not added:
            break
        i += 1
    return out


def notifications(limit: int = 40) -> dict[str, Any]:
    items: list[dict] = []
    for m in fetch_sms(limit=15):
        code = _extract_otp(m.get("text") or "")
        items.append({
            "id": f"sms-{m.get('id', '')}",
            "kind": "sms",
            "source": "phone",
            "title": f"SMS from {m.get('from', '?')}",
            "body": m.get("text") or "",
            "at": m.get("at") or "",
            "ok": True,
            "otp": code,
            "ref": m.get("id"),
        })
    for m in fetch_email(limit=20):
        needs = m.get("needs_reply") in (1, True, "1")
        items.append({
            "id": f"em-{m.get('message_id', m.get('id', ''))}",
            "kind": "email",
            "source": m.get("_mailbox") or m.get("mailbox") or "cmail",
            "title": m.get("subject") or "(no subject)",
            "body": f"{m.get('sender', '?')} · {m.get('summary', '')[:180]}",
            "at": m.get("received_at") or "",
            "ok": not needs,
            "needs_reply": needs,
            "otp": _extract_otp(f"{m.get('subject', '')} {m.get('summary', '')}"),
            "ref": m.get("message_id") or m.get("id"),
        })
    runs, receipts = _local_events(limit=12)
    items.extend(runs)
    items.extend(receipts)
    items.extend(_journal_events(limit=10))
    items.sort(key=lambda n: str(n.get("at") or ""), reverse=True)
    items = items[:limit]
    sms_n = sum(1 for i in items if i["kind"] == "sms")
    email_n = sum(1 for i in items if i["kind"] == "email")
    needs = sum(1 for i in items if i.get("needs_reply") or i.get("otp"))
    return {
        "items": items,
        "counts": {"total": len(items), "sms": sms_n, "email": email_n, "attention": needs},
        "sources": ["phone.sms", "cmail.email", "influence.runs", "qp.receipts", "journal"],
    }


def agent_feed(limit: int = 40) -> dict[str, Any]:
    """Agent-related notifications: receipts, runs, predictions, effects, open tasks."""
    items: list[dict] = []
    runs, receipts = _local_events(limit=20)
    items.extend(runs)
    items.extend(receipts)
    items.extend(_journal_events(limit=15))
    try:
        db = sqlite3.connect(DB_PATH)
        try:
            rows = db.execute(
                "SELECT a.id, a.resource_key, a.title, a.priority, p.slug "
                "FROM human_actions a JOIN projects p ON p.id=a.project_id "
                "WHERE a.done=0 ORDER BY a.priority DESC LIMIT 15"
            ).fetchall()
            for aid, key, title, pri, slug in rows:
                items.append({
                    "id": f"task-{aid}",
                    "kind": "task",
                    "source": "queue",
                    "title": title or key,
                    "body": f"{slug}/{key} · p={pri}",
                    "at": "",
                    "ok": False,
                    "needs_reply": True,
                    "ref": str(aid),
                })
        finally:
            db.close()
    except Exception:
        pass
    items = _sort_feed(items, limit)
    fail = sum(1 for i in items if i["kind"] == "receipt" and not i.get("ok"))
    pending = sum(1 for i in items if i.get("needs_reply"))
    return {
        "items": items,
        "counts": {
            "total": len(items),
            "receipts_fail": fail,
            "pending": pending,
            "runs": sum(1 for i in items if i["kind"] == "run"),
            "tasks": sum(1 for i in items if i["kind"] == "task"),
        },
        "sources": ["influence.runs", "qp.receipts", "hloop.predictions", "journal.effects", "queue.tasks"],
    }
