"""Behavior lock for ported cmail engine. Pins current semantics; edits must update these intentionally."""
import os
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.cmail import engine as E
from core.cmail import models as M
from core.cmail.connectors import CONNECTORS
from core.cmail.connectors.base import Observation


@pytest.fixture()
def db():
    eng = create_engine("sqlite:///:memory:")
    M.Base.metadata.create_all(bind=eng)
    S = sessionmaker(bind=eng)
    s = S()
    yield s
    s.close()


@pytest.fixture()
def stubbed():
    saved = dict(CONNECTORS)
    CONNECTORS["t-ready"] = type("C", (), {"observe": staticmethod(lambda d: Observation("READY", "ok", {"v": 1}))})()
    CONNECTORS["t-missing"] = type("C", (), {"observe": staticmethod(
        lambda d: Observation("MISSING", "need human", {}, "HUMAN", "Do X", "steps", None, 60, 90))})()
    CONNECTORS["t-blocked-auto"] = type("C", (), {"observe": staticmethod(
        lambda d: Observation("BLOCKED", "stuck", {}, "AUTO"))})()
    yield
    CONNECTORS.clear()
    CONNECTORS.update(saved)


def _project(db, slug="p1"):
    p = M.Project(slug=slug, name="P1", passport={"resources": [
        {"key": "a", "kind": "t-ready", "label": "A", "desired": {}},
        {"key": "b", "kind": "t-missing", "label": "B", "desired": {}},
        {"key": "c", "kind": "t-blocked-auto", "label": "C", "desired": {}},
        {"key": "bad-no-kind", "label": "skipped"},
    ]})
    db.add(p)
    db.commit()
    return p


def test_iter_resources_skips_malformed():
    rows = list(E._iter_resources({"resources": [{"key": "x"}, {"kind": "y"}, {"key": "k", "kind": "t"}]}))
    assert [(k, kd) for k, kd, _, _ in rows] == [("k", "t")]


def test_reconcile_counts_progress_and_actions(db, stubbed):
    p = _project(db)
    out = E.reconcile_project(db, p)
    assert out["counts"] == {"READY": 1, "MISSING": 1, "BLOCKED": 1, "UNKNOWN": 0, "ERROR": 0}
    assert out["progress"] == 33  # 1/3 ready
    acts = {a.resource_key for a in p.actions if not a.done}
    assert acts == {"b"}  # only MISSING+HUMAN emits; BLOCKED+AUTO does not


def test_reconcile_clears_resolved_action(db, stubbed):
    p = _project(db)
    E.reconcile_project(db, p)
    assert len([a for a in p.actions if not a.done]) == 1
    p.passport = {"resources": [{"key": "a", "kind": "t-ready", "label": "A", "desired": {}}]}
    db.commit()
    E.reconcile_project(db, p)
    assert [a for a in p.actions if not a.done] == []
    assert {r.key for r in p.resources} == {"a"}  # stale pruned


def test_unknown_connector_kind_is_error(db, stubbed):
    p = M.Project(slug="px", name="PX", passport={"resources": [{"key": "z", "kind": "nope", "label": "Z"}]})
    db.add(p)
    db.commit()
    out = E.reconcile_project(db, p)
    assert out["counts"]["ERROR"] == 1


def test_autopilot_only_runs_auto_apply(db, stubbed):
    ran = []

    class ApplyConn:
        def observe(self, desired):
            return Observation("MISSING", "fix me", {}, "AUTO")
        def apply(self, desired):
            ran.append(desired)
            return {"fixed": True}

    CONNECTORS["t-apply"] = ApplyConn()
    p = M.Project(slug="pa", name="PA", passport={"resources": [
        {"key": "x", "kind": "t-apply", "label": "X", "desired": {"n": 1}},
        {"key": "y", "kind": "t-missing", "label": "Y", "desired": {}},  # HUMAN: skipped
    ]})
    db.add(p)
    db.commit()
    out = E.run_autopilot_project(db, p)
    assert ran == [{"n": 1}]
    # HUMAN-executor resources are skipped silently (continue, not recorded)
    assert out["skipped"] == [] and out["executed"] == [{"key": "x", "result": {"fixed": True}}]
    # stub observe still reports MISSING on re-verify: apply ran, truth unchanged
    assert out["verified"]["counts"]["MISSING"] == 2
