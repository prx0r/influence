"""Drafts queue: proposed content awaiting human approval. Drafts are data;
nothing here can send, publish, or spend. Approval happens through the
decide gate; this store only tracks draft state transitions."""
from __future__ import annotations

import json
import os
import time
import uuid

DRAFTS = os.getenv("DRAFTS_PATH", os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "dash", "drafts.jsonl"))

KINDS = ("post", "mail", "video", "roast", "listing", "message")
STATES = ("OPEN", "APPROVED", "REJECTED", "SENT")


def _load(path: str = DRAFTS) -> list[dict]:
    out = []
    if not os.path.exists(path):
        return out
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    return out


def propose(kind: str, title: str, body: str, meta: dict | None = None,
            path: str = DRAFTS) -> dict:
    if kind not in KINDS:
        raise ValueError(f"unknown draft kind {kind}")
    if not title or not body:
        raise ValueError("title + body required")
    d = {"id": "draft-" + uuid.uuid4().hex[:12], "kind": kind, "title": title,
         "body": body, "meta": meta or {}, "state": "OPEN",
         "ts": int(time.time())}
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(d, sort_keys=True) + "\n")
    return d


def transition(draft_id: str, to: str, note: str = "", path: str = DRAFTS) -> dict:
    """OPEN -> APPROVED|REJECTED; APPROVED -> SENT|REJECTED. Terminal: SENT, REJECTED."""
    if to not in STATES or to == "OPEN":
        raise ValueError(f"bad target {to}")
    items = _load(path)
    cur = next((d for d in reversed(items) if d["id"] == draft_id), None)
    if cur is None:
        raise KeyError(f"unknown draft {draft_id}")
    allowed = {"OPEN": {"APPROVED", "REJECTED"}, "APPROVED": {"SENT", "REJECTED"}}
    if to not in allowed.get(cur["state"], set()):
        raise ValueError(f"illegal {cur['state']}->{to}")
    nxt = dict(cur, state=to, note=note, decided_at=int(time.time()))
    with open(path, "a") as f:
        f.write(json.dumps(nxt, sort_keys=True) + "\n")
    return nxt


def list_open(path: str = DRAFTS) -> list[dict]:
    latest: dict[str, dict] = {}
    for d in _load(path):
        latest[d["id"]] = d
    return [d for d in latest.values() if d["state"] == "OPEN"]
