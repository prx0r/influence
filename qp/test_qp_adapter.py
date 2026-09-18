"""Phase 1 adapter tests: PASS when all READY, FAIL when incomplete,
tamper fails, unknown gate fails, settle replays."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qp.qp_adapter import project_receipt, verify  # noqa: E402


def _res(*statuses):
    kinds = ["domain", "website", "social", "mail"]
    return [{"key": f"k{i}", "kind": kinds[i % len(kinds)],
             "label": f"L{i}", "status": s, "message": "m"}
            for i, s in enumerate(statuses)]


def test_pass_when_all_ready(tmp_path):
    r = project_receipt("t-pass", _res("READY", "READY"),
                        store_path=str(tmp_path / "r.jsonl"))
    assert r["receipt"]["passed"] is True
    assert r["receipt"]["id"].startswith("receipt:")
    assert r["evidence"] and r["receipt"]["evidence_root"]
    assert verify(r["receipt"], r["evidence"])["ok"] is True


def test_fail_when_incomplete(tmp_path):
    r = project_receipt("t-part", _res("READY", "MISSING"),
                        store_path=str(tmp_path / "r.jsonl"))
    assert r["receipt"]["passed"] is False  # UNKNOWN claim: FAIL is first-class
    assert verify(r["receipt"], r["evidence"])["ok"] is False


def test_false_when_blocked(tmp_path):
    r = project_receipt("t-block", _res("READY", "BLOCKED"),
                        store_path=str(tmp_path / "r.jsonl"))
    assert r["claim"]["result"] == "FALSE"
    assert r["receipt"]["passed"] is True  # FALSE resolves claim-resolved-v1


def test_tamper_fails(tmp_path):
    r = project_receipt("t-tamp", _res("READY", "READY"),
                        store_path=str(tmp_path / "r.jsonl"))
    bad = dict(r["receipt"], proof_level=12)
    assert verify(bad, r["evidence"])["ok"] is False
