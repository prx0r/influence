"""Phase 1 adapter: reconcile observations -> qprivately acom receipts.

Imports acom as law (never copied). Each reconcile emits one receipt per
project: evidence per resource, claim TRUE iff all READY / FALSE iff any
BLOCKED / else UNKNOWN, gates fresh + no-duplicate + claim-resolved.
FAIL receipts are first-class, not errors. Appends to JSONL store.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

QPRIVATELY = os.getenv("QPRIVATELY_PATH", "/home/ubuntu/qprivately")
if QPRIVATELY not in sys.path:
    sys.path.insert(0, QPRIVATELY)

import hashlib as _hashlib
import json as _json

from acom import gates as _gates  # noqa: E402,F401 (registry import)
from acom import objects as O  # noqa: E402
from acom import receipts as R  # noqa: E402
from acom import store as StoreMod  # noqa: E402

import sys as _sys
_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent not in _sys.path:
    _sys.path.insert(0, _parent)
from qp.actuality import Actuality, actuality_of_status, and_dag  # noqa: E402

GATES = ["evidence-fresh-v1", "no-duplicate-v1", "claim-resolved-v1"]
RECEIPT_LOG = os.getenv("RECEIPT_LOG", os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "dash", "receipts.jsonl"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def artifact_hash_of(resource: dict) -> str:
    """Content hash of one resource observation. Replaces the old
    sha256:0 placeholder so evidence binds to what was actually seen."""
    canon = _json.dumps(resource, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + _hashlib.sha256(canon).hexdigest()


def adapter_info() -> dict:
    return {"law": "qprivately/acom 0.1", "gates": list(GATES),
            "receipt_log": RECEIPT_LOG}


def project_receipt(slug: str, resources: list[dict],
                    worker: str = "influence-reconcile",
                    store_path: str = RECEIPT_LOG) -> dict:
    """Build evidence + claim + receipt for one project, append to store."""
    now = _now()
    ev = [O.make_evidence(
        metric=f"resource.{r.get('key', '?')}",
        value=r.get("status", "UNKNOWN"),
        unit="status",
        as_of=now,
        source={"class": r.get("kind", "?"),
                "artifact_hash": artifact_hash_of(r),
                "label": r.get("label", ""),
                "message": (r.get("message") or "")[:200]})
        for r in resources]
    acts = [actuality_of_status(r.get("status", "UNKNOWN")) for r in resources]
    proj = and_dag(*acts) if acts else Actuality.TRUE
    claim = O.make_claim(statement=f"project {slug} onboarded",
                         domain="influence.project",
                         result=proj.value)
    run = O.make_run(task_id=claim["id"], worker=worker)
    st = StoreMod.Store(store_path)
    state_before = {"cursor": st.cursor, "rules_commit": "qprivately",
                    "event_root": st.event_root, "state_root": ""}
    receipt = R.transition(
        state_before,
        {"id": claim["id"], "target": claim["id"],
         "claim": claim, "grant": None},
        ev, GATES, run, proof_level=4)
    st.append("transition", {"receipt": receipt, "evidence": ev,
                             "claim": claim, "project": slug})
    return {"receipt": receipt, "evidence": ev, "claim": claim}


def verify(receipt: dict, evidence: list) -> dict:
    """Independent settlement: id check + gate replay."""
    return R.settle(receipt, evidence)
