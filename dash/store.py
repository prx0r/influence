"""Live state for dash: SQLite projects reconciled by core engine. Same shape as seed.json."""
from __future__ import annotations

import json
import os

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from core.cmail import models as M
from core.cmail.engine import project_summary, reconcile_project
from core.cmail.influencer import derive_stage, influencer_passport

try:
    from qp.qp_adapter import project_receipt
    from qp.qp_adapter import adapter_info as _adapter_info
except Exception:  # acom missing: dash still serves, runs carry no proof
    project_receipt = None
    _adapter_info = None

ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("DASH_DB", os.path.join(ROOT, "influence.db"))
SEED_PATH = os.path.join(ROOT, "seed.json")

DIGITS = {"7": "Approve / confirm done", "1": "Hold / replan"}


def _session(db_path: str = DB_PATH):
    eng = create_engine(f"sqlite:///{db_path}")
    M.Base.metadata.create_all(bind=eng)
    return sessionmaker(bind=eng)()


def ensure_seed(db_path: str = DB_PATH) -> None:
    """Explicit seeding only (INFLUENCE_SEED=1). Default backend is clean and empty."""
    if os.getenv("INFLUENCE_SEED", "0") != "1":
        return
    s = _session(db_path)
    try:
        if s.scalar(select(M.Project).limit(1)) is not None:
            return
        with open(SEED_PATH) as f:
            seed = json.load(f)
        for inf in seed["influencers"]:
            handle = inf["slug"].replace("-", "")
            domain = f"{inf['slug']}.dev"
            states = {r["key"]: r["status"] for r in inf["resources"]}
            s.add(M.Project(slug=inf["slug"], name=inf["name"],
                            passport=influencer_passport(handle, domain)))
            # NOTE: seed statuses are display-only until real connectors observe;
            # reconcile below overwrites with honest observations.
            _ = states
        s.commit()
    finally:
        s.close()


def live_state(db_path: str = DB_PATH) -> dict:
    ensure_seed(db_path)
    s = _session(db_path)
    try:
        projects = s.scalars(select(M.Project).order_by(M.Project.id)).all()
        influencers, tasks, runs = [], [], []
        for p in projects:
            rep = reconcile_project(s, p)
            summ = project_summary(p)
            states = {r["key"]: r["status"] for r in summ["resources"]}
            res_list = [{"key": r["key"], "kind": r["kind"], "label": r["label"],
                         "status": r["status"], "message": r["message"] or ""}
                        for r in summ["resources"]]
            influencers.append({
                "slug": p.slug, "name": p.name,
                "stage": derive_stage(states),
                "resources": res_list,
            })
            for a in summ["actions"]:
                tasks.append({"id": f"A-{a['id']}", "influencer": p.slug,
                              "resource_key": a["resource_key"], "kind": "HUMAN",
                              "title": a["title"], "instructions": a["instructions"],
                              "options": DIGITS, "risk": 0.3, "state": "OPEN"})
            run_entry = {"id": f"run-{p.slug}", "influencer": p.slug,
                         "summary": f"Reconcile: {rep['counts']}", "status": "OK"}
            if project_receipt is not None:
                try:
                    pr = project_receipt(p.slug, res_list)
                    rc = pr["receipt"]
                    run_entry.update({
                        "receipt_id": rc["id"],
                        "evidence_root": rc["evidence_root"],
                        "passed": rc["passed"],
                        "gates": [{"id": g["id"], "result": g["result"]}
                                  for g in rc.get("gates", [])],
                    })
                except Exception as exc:
                    # Visible, never silent: dash shows the failure instead
                    # of pretending there is no proof.
                    run_entry["status"] = "RECEIPT_ERROR"
                    run_entry["receipt_error"] = str(exc)[:200]
            else:
                run_entry["status"] = "NO_PROOF"
                run_entry["receipt_error"] = "acom unavailable (QPRIVATELY_PATH)"
            runs.append(run_entry)
        # Resource kinds with no registered connector surface as ERROR with guidance.
        out: dict = {"influencers": influencers, "tasks": tasks, "runs": runs}
        if _adapter_info is not None:
            try:
                out["qp"] = _adapter_info()
            except Exception:
                pass
        return out
    finally:
        s.close()


def mark_resource_done(slug: str, resource_key: str, done: bool = True,
                       db_path: str = DB_PATH) -> dict:
    """Mark a static-checklist resource done/undone in the passport, then
    reconcile. This closes the loop for name/handles/content tasks that
    otherwise stay open forever with no API to complete them."""
    s = _session(db_path)
    try:
        p = s.scalar(select(M.Project).where(M.Project.slug == slug))
        if p is None:
            raise KeyError(f"unknown influencer {slug}")
        passport = dict(p.passport or {})
        resources = [dict(r) for r in passport.get("resources", [])]
        hit = next((r for r in resources if r.get("key") == resource_key), None)
        if hit is None:
            raise KeyError(f"unknown resource {resource_key}")
        desired = dict(hit.get("desired", {}))
        desired["done"] = bool(done)
        hit["desired"] = desired
        passport["resources"] = resources
        # SQLAlchemy JSON mutation: reassign to flag dirty.
        p.passport = passport
        s.commit()
        rep = reconcile_project(s, p)
        summ = project_summary(p)
        return {"slug": slug, "resource_key": resource_key, "done": bool(done),
                "reconcile": rep,
                "statuses": {r["key"]: r["status"] for r in summ["resources"]}}
    finally:
        s.close()


def autopilot_run(slug: str | None = None, db_path: str = DB_PATH) -> dict:
    """Run the conservative autopilot loop (AUTO + apply-capable connectors
    only). Inspection-only connectors are reported as skipped, never forced.
    Exposed for the dash + MCP so the loop is clickable, not dead code."""
    from core.cmail.engine import run_autopilot_all, run_autopilot_project
    s = _session(db_path)
    try:
        if slug:
            p = s.scalar(select(M.Project).where(M.Project.slug == slug))
            if p is None:
                raise KeyError(f"unknown influencer {slug}")
            return run_autopilot_project(s, p)
        return {"results": run_autopilot_all(s)}
    finally:
        s.close()
