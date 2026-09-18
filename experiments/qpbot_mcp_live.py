#!/usr/bin/env python3
"""pq-type live experiment: qpbot stack drives the influence MCP.
T1 remote-agent path (public URL) + T2 qpbot Pi triage + QP receipt.
Logs JSONL to runs/, appends receipt to the receipt log. Never prints tokens.
Run: .venv/bin/python experiments/qpbot_mcp_live.py (needs qpbot dash up)."""
import datetime
import hashlib
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
QPBOT_LOG = "/home/ubuntu/qpbot/dashboard.log"
RUNS = os.path.join(ROOT, "runs")
os.makedirs(RUNS, exist_ok=True)
TS = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
RUNLOG = os.path.join(RUNS, f"qpbot-mcp-{TS}.jsonl")
PUBLIC = "https://influence.intelligentothers.xyz"


def log(**kw):
    kw["ts"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with open(RUNLOG, "a") as f:
        f.write(json.dumps(kw, sort_keys=True) + "\n")
    return kw


def influence_token():
    with open(os.path.join(ROOT, "dash", ".token")) as f:
        return f.read().strip()


def qpbot_token():
    with open(QPBOT_LOG) as f:
        m = re.findall(r"dashboard token: (\S+)", f.read())
    return m[-1]


def post(url, body, timeout=60):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def mcp_remote(name, args):
    return post(f"{PUBLIC}/mcp?token={influence_token()}",
                {"method": "tools/call", "params": {"name": name, "arguments": args}})


def main():
    results = {}
    # T1: remote agent path over the public domain
    tools = post(f"{PUBLIC}/mcp?token={influence_token()}",
                 {"method": "tools/list", "params": {}})["tools"]
    names = sorted(t["name"] for t in tools)
    assert len(names) == 7, names
    log(test="T1-tools-list", ok=True, tools=names)
    q = mcp_remote("queue.list", {})
    assert "result" in q and isinstance(q["result"], list)
    log(test="T1-queue-list", ok=True, open_tasks=len(q["result"]))
    g = mcp_remote("graph.describe", {})
    layers = [x["layer"] for x in g["result"]]
    assert layers[0].startswith("L0") and layers[-1].startswith("L7")
    log(test="T1-graph", ok=True, layers=len(layers))
    results["T1"] = "pass"
    # T2: qpbot Pi triage through its own dash
    chat = post(f"http://127.0.0.1:8791/api/chat?token={qpbot_token()}",
                {"message": "Use the influence MCP: report open tasks count and graph layers."},
                timeout=150)
    reply = chat.get("reply", "")
    assert "queue" in reply.lower() or "task" in reply.lower(), reply[:200]
    log(test="T2-qpbot-triage", ok=True, tools_called=chat.get("tools_called", []),
        reply_chars=len(reply))
    results["T2"] = "pass"
    # Receipt: claim the live verification with tool-output evidence
    sys.path.insert(0, os.getenv("QPRIVATELY_PATH", "/home/ubuntu/qprivately"))
    from acom import objects as O
    from acom import receipts as R
    from acom import store as StoreMod
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    ev = [O.make_evidence("mcp.tools", len(names), "count", now,
                          {"class": "remote", "artifact_hash": "sha256:0"}),
          O.make_evidence("mcp.triage", len(chat.get("tools_called", [])), "count", now,
                          {"class": "qpbot", "artifact_hash": "sha256:0"})]
    claim = O.make_claim("qpbot stack drives influence MCP live", "influence.experiment", "TRUE")
    run = O.make_run(task_id=claim["id"], worker="qpbot-mcp-live")
    st = StoreMod.Store(os.path.join(ROOT, "dash", "receipts.jsonl"))
    rc = R.transition({"cursor": st.cursor, "rules_commit": "qprivately",
                       "event_root": st.event_root, "state_root": ""},
                      {"id": claim["id"], "target": claim["id"], "claim": claim, "grant": None},
                      ev, ["evidence-fresh-v1", "no-duplicate-v1", "claim-resolved-v1"],
                      run, proof_level=4)
    st.append("transition", {"receipt": rc, "evidence": ev, "claim": claim,
                             "experiment": os.path.basename(RUNLOG)})
    log(test="receipt", ok=rc["passed"], receipt_id=rc["id"])
    print(json.dumps({"results": results, "runlog": RUNLOG, "receipt": rc["id"],
                      "passed": rc["passed"]}, indent=1))


if __name__ == "__main__":
    raise SystemExit(main())
