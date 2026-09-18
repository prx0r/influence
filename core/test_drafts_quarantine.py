"""Tests: drafts queue + quarantine pipeline."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.drafts import list_open, propose, transition  # noqa: E402
from core.quarantine import held, hold, review  # noqa: E402


def test_draft_lifecycle(tmp_path):
    p = str(tmp_path / "d.jsonl")
    d = propose("post", "Hello", "world", path=p)
    assert d["state"] == "OPEN" and len(list_open(p)) == 1
    assert transition(d["id"], "APPROVED", "looks good", path=p)["state"] == "APPROVED"
    assert list_open(p) == []
    assert transition(d["id"], "SENT", path=p)["state"] == "SENT"


def test_draft_rejects(tmp_path):
    p = str(tmp_path / "d.jsonl")
    for bad in (lambda: propose("nuke", "t", "b", path=p),
                lambda: propose("post", "", "b", path=p),
                lambda: transition("draft-nope", "APPROVED", path=p)):
        try:
            bad()
            raise SystemExit("draft abuse accepted")
        except (ValueError, KeyError):
            pass
    d = propose("mail", "t", "b", path=p)
    try:
        transition(d["id"], "SENT", path=p)  # OPEN->SENT illegal
        raise SystemExit("skip-approved accepted")
    except ValueError:
        pass


def test_quarantine_downgrade_only(tmp_path):
    p = str(tmp_path / "q.jsonl")
    q = hold({"from": "x", "body": "evil"}, ["override pattern"], path=p)
    assert len(held(p)) == 1
    try:
        hold({"x": 1}, [], path=p)
        raise SystemExit("reasonless hold accepted")
    except ValueError:
        pass
    r = review(q["id"], "CONFIRMED", "real attack, keep as evidence", path=p)
    assert r["state"] == "CONFIRMED" and held(p) == []
    try:
        review(q["id"], "RELEASED", "second look", path=p)
        raise SystemExit("double review accepted")
    except ValueError:
        pass
