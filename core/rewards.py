"""Reward ingestion: audience reactions as evidence. HAHA/CLAP from pogtown
rooms, watch-loop buttons, platform counts — all append as timestamped
reward events keyed to artifact + lineage. Summaries feed reweighting;
raw events stay replayable."""
from __future__ import annotations

import json
import os
import sys
import time

REWARD_LOG = os.getenv("REWARD_LOG", os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "dash", "rewards.jsonl"))
EVAL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "data", "eval", "frozen_v1.json")

SOURCES = ("pogtown", "watch", "youtube", "tiktok", "instagram", "etsy")
REACTIONS = ("haha", "clap", "like", "share", "save", "skip", "order")


def append_reward(artifact: str, lineage: str, reaction: str, count: int = 1,
                  source: str = "watch", log_path: str = REWARD_LOG) -> dict:
    """Append one reward event. Validates shape; raises ValueError on junk."""
    if not artifact or not lineage:
        raise ValueError("artifact + lineage required")
    if reaction not in REACTIONS:
        raise ValueError(f"unknown reaction {reaction}")
    if source not in SOURCES:
        raise ValueError(f"unknown source {source}")
    if not isinstance(count, int) or count < 1:
        raise ValueError("count must be positive int")
    event = {"ts": int(time.time()), "artifact": artifact, "lineage": lineage,
             "reaction": reaction, "count": count, "source": source}
    os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
    with open(log_path, "a") as f:
        f.write(json.dumps(event, sort_keys=True) + "\n")
    return event


def summarize(log_path: str = REWARD_LOG) -> dict:
    """Per-lineage reaction totals + laugh rate. Missing log = empty, never error."""
    totals: dict[str, dict[str, int]] = {}
    if not os.path.exists(log_path):
        return {"lineages": {}, "events": 0}
    n = 0
    with open(log_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except ValueError:
                continue
            n += 1
            t = totals.setdefault(e.get("lineage", "?"), {})
            t[e.get("reaction", "?")] = t.get(e.get("reaction", "?"), 0) + e.get("count", 0)
    out = {}
    for lin, reacts in totals.items():
        pos = reacts.get("haha", 0) + reacts.get("clap", 0) + reacts.get("like", 0)
        neg = reacts.get("skip", 0)
        out[lin] = {"reactions": reacts, "events": sum(reacts.values()),
                    "laugh_rate": round(pos / max(1, pos + neg), 3)}
    return {"lineages": out, "events": n}


def anchor_batch(log_path: str = REWARD_LOG, store_path: str | None = None,
                 as_of: str | None = None) -> dict:
    """Anchor the current reward summary as receipt evidence. The summary is
    computed, evidenced per reaction, claimed TRUE, and receipted — so later
    reweights cite a receipt, not a raw count."""
    from datetime import datetime, timezone
    summary = summarize(log_path)
    if summary["events"] == 0:
        raise ValueError("nothing to anchor")
    now = as_of or datetime.now(timezone.utc).isoformat()
    from qp.law import use_law
    use_law()
    from acom import objects as O
    from acom import receipts as R
    from acom import store as StoreMod
    ev = []
    for lin, data in sorted(summary["lineages"].items()):
        for reaction, count in sorted(data["reactions"].items()):
            ev.append(O.make_evidence(f"reward.{reaction}", count, "count", now,
                                      {"class": "reward", "lineage": lin,
                                       "artifact_hash": "sha256:0"}))
    claim = O.make_claim(f"reward batch: {summary['events']} events", "influence.reward", "TRUE")
    run = O.make_run(task_id=claim["id"], worker="reward-anchor")
    st = StoreMod.Store(store_path or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dash", "receipts.jsonl"))
    receipt = R.transition(
        {"cursor": st.cursor, "rules_commit": "qprivately",
         "event_root": st.event_root, "state_root": ""},
        {"id": claim["id"], "target": claim["id"], "claim": claim, "grant": None},
        ev, ["evidence-fresh-v1", "no-duplicate-v1", "claim-resolved-v1"],
        run, proof_level=4)
    st.append("transition", {"receipt": receipt, "evidence": ev, "claim": claim,
                             "summary": summary})
    return {"receipt": receipt, "evidence": ev, "summary": summary}


def load_eval(path: str = EVAL_PATH) -> dict:
    with open(path) as f:
        ev = json.load(f)
    assert ev.get("version") and isinstance(ev.get("items"), list) and ev["items"]
    for it in ev["items"]:
        assert it.get("id") and it.get("bit") and isinstance(it.get("techniques"), list)
    return ev


def score_against_eval(draft_techniques: list[str], path: str = EVAL_PATH) -> dict:
    """Score a draft's technique set vs frozen eval vocabulary. Returns
    coverage + unknown techniques (which fail closed: unscored, flagged)."""
    ev = load_eval(path)
    vocab = {t for it in ev["items"] for t in it["techniques"]}
    known = [t for t in draft_techniques if t in vocab]
    unknown = [t for t in draft_techniques if t not in vocab]
    score = round(len(known) / max(1, len(draft_techniques)), 3) if draft_techniques else 0.0
    return {"score": score, "known": known, "unknown": unknown,
            "eval_version": ev["version"]}


def reweight(lineage: str, weights: dict[str, float], laugh_rate: float,
             eval_score: float, as_of: str | None = None,
             store_path: str | None = None) -> dict:
    """Deterministic reweight + receipt. Laugh rate pulls weights toward
    techniques present in rewarded artifacts; eval score gates the step:
    eval_score < 0.5 caps the move at half strength. Promotion of the new
    weights happens only via the returned receipt."""
    from datetime import datetime, timezone
    now = as_of or datetime.now(timezone.utc).isoformat()
    pull = laugh_rate * (1.0 if eval_score >= 0.5 else 0.5)
    new_w = {k: round(v * (1.0 + pull), 6) for k, v in weights.items()}
    total = sum(new_w.values()) or 1.0
    new_w = {k: round(v / total, 6) for k, v in new_w.items()}

    from qp.law import use_law
    use_law()
    from acom import objects as O
    from acom import receipts as R
    from acom import store as StoreMod
    ev = [O.make_evidence("reward.laugh_rate", laugh_rate, "rate", now,
                          {"class": "reward", "artifact_hash": "sha256:0"}),
          O.make_evidence("eval.score", eval_score, "score", now,
                          {"class": "eval", "artifact_hash": "sha256:0"})]
    claim = O.make_claim(f"lineage {lineage} reweighted", "influence.lineage", "TRUE")
    run = O.make_run(task_id=claim["id"], worker="funnylab-reweight")
    st = StoreMod.Store(store_path or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dash", "receipts.jsonl"))
    receipt = R.transition(
        {"cursor": st.cursor, "rules_commit": "qprivately",
         "event_root": st.event_root, "state_root": ""},
        {"id": claim["id"], "target": claim["id"], "claim": claim, "grant": None},
        ev, ["evidence-fresh-v1", "no-duplicate-v1", "claim-resolved-v1"],
        run, proof_level=4)
    st.append("transition", {"receipt": receipt, "evidence": ev, "claim": claim,
                             "lineage": lineage, "weights": new_w})
    return {"lineage": lineage, "weights": new_w, "receipt": receipt, "evidence": ev}
