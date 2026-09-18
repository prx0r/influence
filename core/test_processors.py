"""Tests: processors propose-only. Forbidden keys abort; schema enforced."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.processors import PROCESSOR_FNS, PROCESSORS, run_processor  # noqa: E402


def test_registry_runs():
    p = run_processor(PROCESSORS["draft.write"], {"topic": "sleep"}, PROCESSOR_FNS["draft.write"])
    assert p.failure is None and "draft" in p.outputs and p.evidence
    s = run_processor(PROCESSORS["set.write"], {"premise": "cats", "techniques": ["callback"]},
                      PROCESSOR_FNS["set.write"])
    assert len(s.outputs["set"]) == 1 and s.failure is None


def test_schema_rejects_extra_input():
    try:
        run_processor(PROCESSORS["draft.write"], {"topic": "x", "grant": "forged"},
                      PROCESSOR_FNS["draft.write"])
        raise SystemExit("extra input accepted")
    except ValueError:
        pass


def test_forbidden_output_aborts():
    evil = lambda inputs: {"draft": "x", "receipt": "forged", "spend": 1}
    p = run_processor(PROCESSORS["draft.write"], {"topic": "x"}, evil)
    assert p.failure and "receipt" in p.failure and not p.outputs
    for key in ("state_after", "grant", "signature", "mint", "send"):
        q = run_processor(PROCESSORS["draft.write"], {"topic": "x"},
                          lambda i, k=key: {"draft": "x", k: 1})
        assert q.failure, key
