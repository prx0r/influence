#!/usr/bin/env python3
"""live_sweep.py — pq-style logged testing for the influence dash + MCP.

Every check logs JSONL to runs/. Every finding gets a QP receipt in the
receipt log. Nothing is trusted — everything is verified.

Usage:
  DASH_PORT=8794 DASH_TOKEN=... LIVE=0 .venv/bin/python experiments/live_sweep.py
  # boots nothing itself: point it at a running dash (see dash/serve.sh)

Rules (mirrors pq):
  1. Every check logs to runs/. No silent runs.
  2. Every finding gets a QP receipt. No unverified claims.
  3. Tokens stay in env. Never printed, never logged.
"""
import datetime
import json
import os
import sys
import urllib.request
import urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from qp.law import use_law
use_law()

PORT = os.getenv("DASH_PORT", "8793")
TOKEN = os.getenv("DASH_TOKEN", "")
BASE = f"http://127.0.0.1:{PORT}"
TS = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
RUNLOG = os.path.join(ROOT, "runs", f"sweep-{TS}.jsonl")
os.makedirs(os.path.join(ROOT, "runs"), exist_ok=True)

GATES = ["evidence-fresh-v1", "no-duplicate-v1", "claim-resolved-v1"]


def log(check, passed, details=None):
    entry = {"ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
             "run": TS, "live": os.getenv("LIVE", "0"),
             "check": check, "passed": bool(passed)}
    if details:
        entry["details"] = details
    with open(RUNLOG, "a") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry


def receipt_for(check, passed, notes=""):
    """One QP receipt per finding, appended to the receipt log."""
    from acom import objects as O
    from acom import receipts as R
    from acom import store as StoreMod
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    ev = [O.make_evidence(metric=f"sweep.{check}",
                          value="PASS" if passed else "FAIL", unit="verdict",
                          as_of=now,
                          source={"class": "live-sweep",
                                  "artifact_hash": "sha256:sweep",
                                  "label": check, "message": notes[:200]})]
    claim = O.make_claim(statement=f"sweep check {check} {'passed' if passed else 'failed'}",
                         domain="influence.sweep",
                         result="TRUE" if passed else "FALSE")
    run = O.make_run(task_id=claim["id"], worker="influence-sweep")
    store_path = os.getenv("RECEIPT_LOG", os.path.join(ROOT, "dash", "receipts.jsonl"))
    st = StoreMod.Store(store_path)
    state_before = {"cursor": st.cursor, "rules_commit": "qprivately",
                    "event_root": st.event_root, "state_root": ""}
    rc = R.transition(state_before, {"id": claim["id"], "target": claim["id"],
                                     "claim": claim, "grant": None},
                      ev, GATES, run, proof_level=4)
    st.append("transition", {"receipt": rc, "evidence": ev,
                             "claim": claim, "project": f"sweep-{TS}"})
    return rc["id"]


def check(name, fn):
    try:
        notes = fn() or ""
        rid = receipt_for(name, True, str(notes))
        log(name, True, {"notes": str(notes)[:200], "receipt": rid})
        print(f"PASS {name} [{rid}]")
        return True
    except AssertionError as e:
        rid = receipt_for(name, False, str(e))
        log(name, False, {"error": str(e)[:200], "receipt": rid})
        print(f"FAIL {name} [{rid}]: {e}")
        return False
    except Exception as e:
        log(name, False, {"error": f"{type(e).__name__}: {str(e)[:200]}"})
        print(f"ERROR {name}: {type(e).__name__} {str(e)[:160]}")
        return False


def _req(method, path, body=None):
    url = BASE + path
    if TOKEN:
        url += ("&" if "?" in path else "?") + f"token={TOKEN}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json",
                                          # Cloudflare edge 403s Python-urllib UA;
                                          # identify honestly instead of looking like a bot.
                                          "User-Agent": "influence-sweep/1.0"},
                                 method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except ValueError:
            return e.code, {}


def get(path):
    return _req("GET", path)


def post(path, body):
    return _req("POST", path, body)


def main():
    results = []

    def t_health():
        s, b = get("/api/health")
        assert s == 200 and b.get("ok") is True, f"health {s} {b}"
        return "dash=influence"
    results.append(check("health", t_health))

    state = {}

    def t_state():
        nonlocal state
        s, b = get("/api/state")
        assert s == 200, f"state status {s}"
        for k in ("influencers", "tasks", "runs"):
            assert k in b, f"missing {k}"
        state.update(b)
        return f"{len(b['influencers'])} influencers, {len(b['tasks'])} tasks, {len(b['runs'])} runs"
    results.append(check("state-shape", t_state))

    def t_receipts_visible():
        runs = state.get("runs", [])
        if not runs:
            return "no runs yet (empty backend, honest)"
        with_proof = [r for r in runs if r.get("receipt_id")]
        broken = [r for r in runs if r.get("status") in ("RECEIPT_ERROR", "NO_PROOF")]
        assert not broken, f"runs without proof: {broken}"
        return f"{len(with_proof)}/{len(runs)} runs carry receipts"
    results.append(check("runs-carry-receipts", t_receipts_visible))

    def t_mcp_list():
        s, b = post("/mcp", {"method": "tools/list", "params": {}})
        assert s == 200, f"mcp list {s}"
        names = sorted(t["name"] for t in b["tools"])
        assert "influencer.list" in names and "receipt.get" in names, names
        return ",".join(names)
    results.append(check("mcp-list", t_mcp_list))

    def t_mcp_calls():
        s, b = post("/mcp", {"method": "tools/call",
                             "params": {"name": "influencer.list", "arguments": {}}})
        assert s == 200 and "result" in b, b
        s, b = post("/mcp", {"method": "tools/call",
                             "params": {"name": "queue.list", "arguments": {}}})
        assert s == 200 and "result" in b, b
        s, b = post("/mcp", {"method": "tools/call",
                             "params": {"name": "graph.describe", "arguments": {}}})
        assert s == 200 and len(b.get("result", [])) == 8, b
        s, b = post("/mcp", {"method": "tools/call",
                             "params": {"name": "product.list", "arguments": {}}})
        assert s == 200 and len(b.get("result", [])) >= 16, b
        return "list/get/queue/graph/products ok"
    results.append(check("mcp-calls", t_mcp_calls))

    def t_buys_blocked():
        for evil in ("xmr.pay", "spend.authorize", "post.publish",
                     "mail.send", "buy.now", "domain.register"):
            s, b = post("/mcp", {"method": "tools/call",
                                 "params": {"name": evil, "arguments": {}}})
            assert "error" in b, f"{evil} not blocked: {b}"
        return "6/6 spend/send/buy tools rejected"
    results.append(check("buys-blocked", t_buys_blocked))

    def t_chat():
        s, b = post("/api/chat", {"message": "/help"})
        assert s == 200 and "/add" in b.get("reply", ""), b
        s, b = post("/api/chat", {"message": "/status"})
        assert s == 200 and "influencers" in b.get("reply", ""), b
        return "help+status answer"
    results.append(check("chat", t_chat))

    def t_decide_gate():
        tasks = state.get("tasks", [])
        if not tasks:
            log("decide-gate", True, {"notes": "SKIP: empty backend, no tasks to decide"})
            print("SKIP decide-gate (no tasks — honest empty backend)")
            return True
        tid = tasks[0]["id"]
        s, _ = post("/api/decide", {"task_id": tid, "digit": "7"})
        assert s == 409, f"decide without present must 409, got {s}"
        s, b = post("/api/present", {"task_id": tid})
        assert s == 200 and b.get("prediction_ref"), b
        ref = b["prediction_ref"]
        s, b = post("/api/decide", {"task_id": tid, "digit": "7",
                                    "prediction_ref": ref})
        assert s == 200 and b.get("state") == "APPROVED_PENDING_QP", b
        return f"{tid} present->decide, intent only, nothing executed"
    results.append(check("decide-gate", t_decide_gate))

    def t_verify_chain():
        sys.path.insert(0, ROOT)
        from validation.verify import verify_log
        store_path = os.getenv("RECEIPT_LOG", os.path.join(ROOT, "dash", "receipts.jsonl"))
        v = verify_log(store_path)
        assert v["ok"], f"chain broken: {v}"
        return f"chained, {v['checked']} receipts re-settled, 0 failed"
    results.append(check("verify-chain", t_verify_chain))

    n = sum(1 for r in results if r)
    print(f"\nSWEEP {TS}: {n}/{len(results)} passed — log {RUNLOG}")
    return 0 if n == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
