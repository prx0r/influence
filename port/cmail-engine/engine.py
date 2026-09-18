from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .connectors import CONNECTORS
from .models import HumanAction, Project, ResourceState, RunLog


def _iter_resources(passport: dict[str, Any]) -> Iterable[tuple[str, str, str, dict[str, Any]]]:
    """Yield key, kind, label, desired from a passport.

    Passport resources are deliberately generic so new adapters do not require DB migrations.
    """
    for resource in passport.get("resources", []):
        if not resource.get("key") or not resource.get("kind"):
            continue
        yield resource["key"], resource["kind"], resource.get("label") or resource["key"], resource.get("desired", {})


def _upsert_resource(db: Session, project: Project, key: str, kind: str, label: str, desired: dict, observation) -> ResourceState:
    row = db.scalar(select(ResourceState).where(ResourceState.project_id == project.id, ResourceState.key == key))
    if row is None:
        row = ResourceState(project_id=project.id, key=key, kind=kind, label=label)
        db.add(row)
    row.kind = kind
    row.label = label
    row.status = observation.status
    row.desired = desired
    row.observed = observation.observed
    row.message = observation.message
    row.executor = observation.executor
    return row


def _sync_action(db: Session, project: Project, key: str, observation) -> None:
    row = db.scalar(select(HumanAction).where(HumanAction.project_id == project.id, HumanAction.resource_key == key))
    needs_human = observation.status in {"MISSING", "BLOCKED", "UNKNOWN"} and observation.executor == "HUMAN"
    if not needs_human:
        if row and not row.done:
            db.delete(row)
        return
    if row is None:
        row = HumanAction(project_id=project.id, resource_key=key, title="", instructions="")
        db.add(row)
    row.title = observation.human_title or observation.message
    row.instructions = observation.human_instructions or observation.message
    row.url = observation.human_url
    row.estimate_seconds = observation.estimate_seconds
    row.priority = observation.priority
    row.done = False
    row.completed_at = None


def reconcile_project(db: Session, project: Project) -> dict[str, Any]:
    log = RunLog(project_id=project.id)
    db.add(log)
    db.flush()

    keys_seen: set[str] = set()
    counts: dict[str, int] = {"READY": 0, "MISSING": 0, "BLOCKED": 0, "UNKNOWN": 0, "ERROR": 0}
    for key, kind, label, desired in _iter_resources(project.passport or {}):
        keys_seen.add(key)
        connector = CONNECTORS.get(kind)
        if connector is None:
            from .connectors.base import Observation
            observation = Observation("ERROR", f"No connector registered for kind={kind}")
        else:
            observation = connector.observe(desired)
        _upsert_resource(db, project, key, kind, label, desired, observation)
        _sync_action(db, project, key, observation)
        counts[observation.status] = counts.get(observation.status, 0) + 1

    stale = db.scalars(select(ResourceState).where(ResourceState.project_id == project.id)).all()
    for row in stale:
        if row.key not in keys_seen:
            db.delete(row)
    stale_actions = db.scalars(select(HumanAction).where(HumanAction.project_id == project.id)).all()
    for row in stale_actions:
        if row.resource_key not in keys_seen:
            db.delete(row)

    total = sum(counts.values())
    ready = counts.get("READY", 0)
    progress = round(100 * ready / total) if total else 100
    log.status = "OK" if not counts.get("ERROR") else "PARTIAL"
    log.finished_at = datetime.now(timezone.utc)
    log.summary = {"counts": counts, "progress": progress}
    db.commit()
    return {"project": project.slug, "counts": counts, "progress": progress}


def reconcile_all(db: Session) -> list[dict[str, Any]]:
    projects = db.scalars(select(Project).order_by(Project.id)).all()
    return [reconcile_project(db, p) for p in projects]


def project_summary(project: Project) -> dict[str, Any]:
    resources = list(project.resources)
    ready = sum(1 for r in resources if r.status == "READY")
    expected = len((project.passport or {}).get("resources", []))
    progress = round(100 * ready / len(resources)) if resources else (100 if expected == 0 else 0)
    actions = sorted((a for a in project.actions if not a.done), key=lambda a: (-a.priority, a.id))
    return {
        "id": project.id,
        "slug": project.slug,
        "name": project.name,
        "domain": project.domain,
        "progress": progress,
        "resources": [{
            "key": r.key, "kind": r.kind, "label": r.label, "status": r.status,
            "message": r.message, "executor": r.executor, "observed": r.observed,
        } for r in sorted(resources, key=lambda x: x.id)],
        "actions": [{
            "id": a.id, "resource_key": a.resource_key, "title": a.title,
            "instructions": a.instructions, "url": a.url,
            "estimate_seconds": a.estimate_seconds, "priority": a.priority, "done": a.done,
        } for a in actions],
    }


def run_autopilot_project(db: Session, project: Project) -> dict[str, Any]:
    """Execute only connector actions that are explicitly AUTO and locally safe.

    Connectors without an `apply` method are inspection-only in the MVP. This keeps
    external mutation conservative while proving the full observe -> act -> verify loop.
    """
    reconcile_project(db, project)
    db.refresh(project)
    resources = db.scalars(select(ResourceState).where(ResourceState.project_id == project.id)).all()
    executed: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for resource in resources:
        if resource.status == "READY" or resource.executor != "AUTO":
            continue
        connector = CONNECTORS.get(resource.kind)
        apply_fn = getattr(connector, "apply", None) if connector else None
        if apply_fn is None:
            skipped.append({"key": resource.key, "reason": "connector is inspection-only"})
            continue
        try:
            result = apply_fn(resource.desired)
            executed.append({"key": resource.key, "result": result})
        except Exception as exc:
            skipped.append({"key": resource.key, "reason": str(exc)})
    verified = reconcile_project(db, project)
    return {"project": project.slug, "executed": executed, "skipped": skipped, "verified": verified}


def run_autopilot_all(db: Session) -> list[dict[str, Any]]:
    projects = db.scalars(select(Project).order_by(Project.id)).all()
    return [run_autopilot_project(db, p) for p in projects]
