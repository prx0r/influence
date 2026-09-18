"""Tests: verifier independence (stdlib+acom only), chain + replay checks,
tamper detection."""
import ast
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from validation.verify import verify_log  # noqa: E402


def test_import_boundary():
    tree = ast.parse(open(os.path.join(os.path.dirname(__file__), "verify.py")).read())
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                roots.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                roots.add(node.module.split(".")[0])
    allowed = {"acom", "json", "os", "sys"}
    assert roots <= allowed, roots - allowed


def _seed(path):
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "law"))
    from qp.law import use_law
    use_law()
    from acom import objects as O
    from acom import receipts as R
    from acom import store as StoreMod
    st = StoreMod.Store(path)
    ev = [O.make_evidence("m", 1, "u", "2026-01-01T00:00:00+00:00",
                          {"class": "t", "artifact_hash": "sha256:0"}),
          O.make_evidence("m", 2, "u", "2026-01-01T00:00:00+00:00",
                          {"class": "t", "artifact_hash": "sha256:0"})]
    claim = O.make_claim("s", "d", "TRUE")
    run = O.make_run(task_id=claim["id"], worker="w")
    rc = R.transition({"cursor": 0, "rules_commit": "t", "event_root": "", "state_root": ""},
                      {"id": claim["id"], "target": claim["id"], "claim": claim, "grant": None},
                      ev, ["evidence-fresh-v1", "no-duplicate-v1", "claim-resolved-v1"],
                      run, proof_level=4)
    st.append("transition", {"receipt": rc, "evidence": ev, "claim": claim})
    return rc


def test_verify_clean_and_tampered(tmp_path):
    good = str(tmp_path / "good.jsonl")
    _seed(good)
    rep = verify_log(good)
    assert rep == {"chained": True, "checked": 1, "failed": [], "ok": True}
    bad = str(tmp_path / "bad.jsonl")
    _seed(bad)
    with open(bad, "a") as f:
        f.write('{"seq":99,"type":"evil","payload":{},"prev":"x","hash":"y"}\n')
    rep2 = verify_log(bad)
    assert rep2["chained"] is False and rep2["ok"] is False
