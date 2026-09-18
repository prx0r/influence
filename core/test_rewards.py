"""Tests: reward ingestion, frozen eval, scoring, reweight + receipt."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.rewards import anchor_batch, append_reward, load_eval, reweight, score_against_eval, summarize  # noqa: E402


def test_append_validates(tmp_path):
    log = str(tmp_path / "r.jsonl")
    e = append_reward("set-1", "absurd", "haha", 3, "pogtown", log)
    assert e["count"] == 3 and e["source"] == "pogtown"
    for bad in ({"artifact": "", "lineage": "a", "reaction": "haha"},
                {"artifact": "x", "lineage": "", "reaction": "haha"},
                {"artifact": "x", "lineage": "a", "reaction": "lol"},
                {"artifact": "x", "lineage": "a", "reaction": "haha", "source": "nope"},
                {"artifact": "x", "lineage": "a", "reaction": "haha", "count": 0}):
        try:
            append_reward(bad.get("artifact", "x"), bad.get("lineage", "a"),
                          bad.get("reaction", "haha"), bad.get("count", 1),
                          bad.get("source", "watch"), log)
            raise SystemExit(f"accepted junk {bad}")
        except ValueError:
            pass


def test_summarize_rates(tmp_path):
    log = str(tmp_path / "r.jsonl")
    append_reward("s1", "absurd", "haha", 4, "pogtown", log)
    append_reward("s1", "absurd", "skip", 1, "pogtown", log)
    append_reward("s2", "roast", "clap", 2, "watch", log)
    s = summarize(log)
    assert s["lineages"]["absurd"]["laugh_rate"] == 0.8
    assert s["events"] == 3
    assert summarize(str(tmp_path / "missing.jsonl")) == {"lineages": {}, "events": 0}


def test_eval_loads_and_scores():
    ev = load_eval()
    assert ev["version"] == "frozen_v1" and len(ev["items"]) == 8
    r = score_against_eval(["absurdism", "callback", "invented-thing"])
    assert r["known"] == ["absurdism", "callback"] and r["unknown"] == ["invented-thing"]
    assert r["eval_version"] == "frozen_v1"


def test_anchor_batch_receipt(tmp_path):
    log = str(tmp_path / "r.jsonl")
    try:
        anchor_batch(log, store_path=str(tmp_path / "rc.jsonl"))
        raise SystemExit("empty anchor accepted")
    except ValueError:
        pass
    append_reward("s1", "absurd", "haha", 4, "pogtown", log)
    append_reward("s1", "absurd", "skip", 1, "pogtown", log)
    a = anchor_batch(log, store_path=str(tmp_path / "rc.jsonl"),
                     as_of="2026-01-01T00:00:00+00:00")
    assert a["receipt"]["passed"] is True
    assert a["summary"]["lineages"]["absurd"]["laugh_rate"] == 0.8


def test_reweight_deterministic_receipt(tmp_path):
    w = {"absurdism": 0.5, "deadpan": 0.5}
    a = reweight("absurd", w, 0.8, 0.75, as_of="2026-01-01T00:00:00+00:00",
                 store_path=str(tmp_path / "rc.jsonl"))
    b = reweight("absurd", w, 0.8, 0.75, as_of="2026-01-01T00:00:00+00:00",
                 store_path=str(tmp_path / "rc2.jsonl"))
    assert a["receipt"]["id"] == b["receipt"]["id"]  # deterministic
    assert a["receipt"]["passed"] is True
    assert abs(sum(a["weights"].values()) - 1.0) < 1e-6
    assert a["weights"]["absurdism"] == b["weights"]["absurdism"]
    lines = open(tmp_path / "rc.jsonl").read().strip().split("\n")
    assert json.loads(lines[-1])["payload"]["lineage"] == "absurd"
