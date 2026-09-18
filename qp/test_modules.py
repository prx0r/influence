"""Modules: scope membership is provable, masquerading fails."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qp.law import use_law
use_law()
from acom import objects as O
from acom import receipts as R
from acom import store as StoreMod
from qp.modules import MODULES, module_of_domain, scope_check


def _receipt(domain, gate_ids, tmp):
    now = "2026-09-18T00:00:00+00:00"
    ev = [O.make_evidence("m", 1, "u", now, {"class": "t", "artifact_hash": "sha256:0"})]
    claim = O.make_claim("s", domain, "TRUE")
    run = O.make_run(task_id=claim["id"], worker="t")
    st = StoreMod.Store(str(tmp / "s.jsonl"))
    rc = R.transition({"cursor": st.cursor, "rules_commit": "q",
                       "event_root": st.event_root, "state_root": ""},
                      {"id": claim["id"], "target": claim["id"],
                       "claim": claim, "grant": None},
                      ev, gate_ids, run, proof_level=0)
    return rc


def test_known_domains_map(tmp_path):
    rc = _receipt("influence.project", ["evidence-fresh-v1", "no-duplicate-v1",
                                        "claim-resolved-v1"], tmp_path)
    v = scope_check(rc)
    assert v == {"ok": True, "module": "provision", "reason": "3 gates within provision"}


def test_unregistered_domain_fails(tmp_path):
    rc = _receipt("influence.elsewhere", ["evidence-fresh-v1"], tmp_path)
    v = scope_check(rc)
    assert v["ok"] is False and v["module"] is None


def test_foreign_gate_fails_scope(tmp_path):
    rc = _receipt("influence.spend", ["evidence-fresh-v1", "no-duplicate-v1",
                                      "claim-resolved-v1", "two-sources-v1"], tmp_path)
    v = scope_check(rc)
    assert v["ok"] is False and v["module"] == "ledger"


def test_registry_covers_receipt_log():
    import json
    log = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "dash", "receipts.jsonl")
    if not os.path.exists(log):
        import pytest
        pytest.skip("no receipt log on this box")
    n, bad = 0, []
    with open(log) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rc = json.loads(line)["payload"]["receipt"]
            v = scope_check(rc)
            n += 1
            if not v["ok"]:
                bad.append((rc.get("id"), v["reason"]))
    assert n > 0, "receipt log empty"
    assert not bad, f"out-of-scope receipts: {bad[:5]}"
