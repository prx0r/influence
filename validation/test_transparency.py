"""Tests: inclusion proofs roundtrip, tamper fails, receipt-level proof."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from validation.transparency import inclusion_proof, receipt_inclusion, root_of, verify_inclusion  # noqa: E402
from validation.verify import verify_log  # noqa: E402


def test_roundtrip_sizes():
    for n in (1, 2, 3, 5, 8):
        leaves = [f"leaf{i}" for i in range(n)]
        for i in range(n):
            p = inclusion_proof(leaves, i)
            assert p["root"] == root_of(leaves)
            assert verify_inclusion(p) is True


def test_tamper_fails():
    leaves = ["a", "b", "c"]
    p = inclusion_proof(leaves, 0)
    assert verify_inclusion({**p, "root": "00" * 32}) is False
    q = inclusion_proof(leaves, 1)
    q["siblings"][0][1] = "ff" * 32
    assert verify_inclusion(q) is False
    try:
        inclusion_proof([], 0)
        raise SystemExit("empty proof accepted")
    except IndexError:
        pass


def test_receipt_level(tmp_path):
    import sys as _sys
    _sys.path.insert(0, "/home/ubuntu/qprivately")
    from acom import objects as O
    from acom import receipts as R
    from acom import store as StoreMod
    path = str(tmp_path / "t.jsonl")
    st = StoreMod.Store(path)
    ev = [O.make_evidence("m", 1, "u", "2026-01-01T00:00:00+00:00",
                          {"class": "t", "artifact_hash": "sha256:0"})]
    claim = O.make_claim("s", "d", "TRUE")
    run = O.make_run(task_id=claim["id"], worker="w")
    rc = R.transition({"cursor": 0, "rules_commit": "t", "event_root": "", "state_root": ""},
                      {"id": claim["id"], "target": claim["id"], "claim": claim, "grant": None},
                      ev, ["evidence-fresh-v1", "no-duplicate-v1", "claim-resolved-v1"],
                      run, proof_level=4)
    st.append("transition", {"receipt": rc, "evidence": ev, "claim": claim})
    proof = receipt_inclusion(path, rc["id"])
    assert proof and verify_inclusion(proof) is True
    assert proof["root"] == st.event_root  # same root the store reports
    assert receipt_inclusion(path, "receipt:nope") is None
    assert verify_log(path)["ok"] is True
