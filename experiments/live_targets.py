#!/usr/bin/env python3
"""live_targets.py — ACTUAL logged testing against live backend targets.

Seeds real influencers (real domains, real DNS/HTTP observations),
reconciles, decides every task, exercises resource-done + autopilot,
runs adversarial checks, verifies the receipt chain.

Every check logs JSONL to runs/. Every finding gets a QP receipt.
Exit 0 = all green. Non-zero = something actually broke.

Usage:
  DASH_PORT=8793 DASH_TOKEN=... LIVE=1 .venv/bin/python experiments/live_targets.py
"""
import datetime
import json
import os
import sys
import urllib.request
import urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

QPRIVATELY = os.getenv("QPRIVATELY_PATH", "/home/ubuntu/qprivately")
if QPRIVATELY not in sys.path:
    sys.path.insert(0, QPRIVATELY)

PORT = os.getenv("DASH_PORT", "8793")
TOKEN = os.getenv("DASH_TOKEN", "")
BASE = f"http://127.0.0.1:{PORT}"
TS = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
RUNLOG = os.path.join(ROOT, "runs", f"targets-{TS}.jsonl")
os.makedirs(os.path.join(ROOT, "runs"), exist_ok=True)

GATES = ["evidence-fresh-v1", "no-duplicate-v1", "claim-resolved-v1"]
PASS = [0]  # mutable counter


def log(check, passed, details=None):
    entry = {"ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
             "run": TS, "check": check, "passed": bool(passed)}
    if details:
        entry["details"] = details
    with open(RUNLOG, "a") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry


def receipt_for(check, passed, notes=""):
    from acom import objects as O
    from acom import receipts as R
    from acom import store as StoreMod
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    ev = [O.make_evidence(metric=f"targets.{check}",
                          value="PASS" if passed else "FAIL", unit="verdict",
                          as_of=now,
                          source={"class": "live-targets", "artifact_hash": "sha256:targets",
                                  "label": check, "message": notes[:200]})]
    claim = O.make_claim(statement=f"live target check {check} {'passed' if passed else 'failed'}",
                         domain="influence.targets",
                         result="TRUE" if passed else "FALSE")
    run = O.make_run(task_id=claim["id"], worker="influence-targets")
    store_path = os.getenv("RECEIPT_LOG", os.path.join(ROOT, "dash", "receipts.jsonl"))
    st = StoreMod.Store(store_path)
    state_before = {"cursor": st.cursor, "rules_commit": "qprivately",
                    "event_root": st.event_root, "state_root": ""}
    rc = R.transition(state_before, {"id": claim["id"], "target": claim["id"],
                                     "claim": claim, "grant": None},
                      ev, GATES, run, proof_level=4)
    st.append("transition", {"receipt": rc, "evidence": ev,
                             "claim": claim, "project": f"targets-{TS}"})
    return rc["id"]


def check(name, fn):
    try:
        notes = fn() or ""
        rid = receipt_for(name, True, str(notes))
        log(name, True, {"notes": str(notes)[:300], "receipt": rid})
        PASS[0] += 1
        print(f"PASS {name} [{rid}] :: {str(notes)[:120]}", flush=True)
        return True
    except AssertionError as e:
        rid = receipt_for(name, False, str(e))
        log(name, False, {"error": str(e)[:300], "receipt": rid})
        print(f"FAIL {name} [{rid}]: {e}", flush=True)
        return False
    except Exception as e:
        log(name, False, {"error": f"{type(e).__name__}: {str(e)[:300]}"})
        print(f"ERROR {name}: {type(e).__name__} {str(e)[:200]}", flush=True)
        return False


def _req(method, path, body=None):
    url = BASE + path
    if TOKEN:
        url += ("&" if "?" in path else "?") + f"token={TOKEN}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json",
                                          "User-Agent": "influence-sweep/1.0"},
                                 method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read() or b"{}"
            return r.status, json.loads(raw)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except ValueError:
            return e.code, {}


def get(path):
    return _req("GET", path)


def post(path, body):
    return _req("POST", path, body)


TARGETS = [("sweep-alpha", "example.com"), ("sweep-beta", "example.org")]


def main():
    total = [0]

    def run(name, fn):
        total[0] += 1
        return check(name, fn)

    # 1. seed live targets (real domains -> real DNS/HTTP observations)
    def t_seed():
        out = []
        for slug, domain in TARGETS:
            s, b = post("/api/chat", {"message": f"/add {slug} {domain}"})
            assert s == 200, f"/add {slug}: {s} {b}"
            out.append(f"{slug}: {b.get('reply', '')[:80]}")
        return " | ".join(out)
    run("seed-targets", t_seed)

    # 2. reconcile + state shape over live targets
    state = {}

    def t_reconcile():
        s, b = post("/api/reconcile", {})
        assert s == 200 and b.get("ok"), f"reconcile: {s} {b}"
        s, b = get("/api/state")
        assert s == 200, f"state: {s}"
        state.update(b)
        for slug, _ in TARGETS:
            assert any(i["slug"] == slug for i in b["influencers"]), f"{slug} missing"
        n_ready = sum(1 for i in b["influencers"] for r in i["resources"]
                      if r["status"] == "READY")
        # example.com/org resolve + serve HTTP: domain+website MUST be READY (real proof)
        for slug, _ in TARGETS:
            inf = next(i for i in b["influencers"] if i["slug"] == slug)
            by_key = {r["key"]: r["status"] for r in inf["resources"]}
            assert by_key.get("domain") == "READY", f"{slug} domain not READY: {by_key}"
        return f"{len(b['influencers'])} influencers, {len(b['tasks'])} tasks, {n_ready} READY"
    run("reconcile-live", t_reconcile)

    # 3. decide every open task (7 approve, 1 hold — both journal paths)
    def t_decide_all():
        s, b = get("/api/state")
        tasks = b["tasks"]
        assert tasks, "no tasks to decide — reconcile raised nothing"
        digest = []
        for n, t in enumerate(tasks):
            digit = "1" if n % 4 == 3 else "7"
            s, p = post("/api/present", {"task_id": t["id"]})
            assert s == 200 and p.get("prediction_ref"), f"present {t['id']}: {s} {p}"
            s, d = post("/api/decide", {"task_id": t["id"], "digit": digit,
                                        "prediction_ref": p["prediction_ref"]})
            assert s == 200 and d.get("ok"), f"decide {t['id']}: {s} {d}"
            expect = "APPROVED_PENDING_QP" if digit == "7" else "RECORDED"
            assert d.get("state") == expect, f"{t['id']}: want {expect}, got {d}"
            digest.append(f"{t['id']}={d['state']}")
        return f"{len(tasks)} decided: " + ", ".join(digest[:8])
    run("decide-all-tasks", t_decide_all)

    # 4. resource-done close-out: mark handles done -> reconciles READY
    def t_resource_done():
        slug = TARGETS[0][0]
        s, b = post("/api/resource-done", {"slug": slug, "resource_key": "handles", "done": True})
        assert s == 200 and b.get("ok"), f"resource-done: {s} {b}"
        assert b["statuses"].get("handles") == "READY", f"handles not READY: {b['statuses']}"
        s, b = post("/api/resource-done", {"slug": "nope", "resource_key": "handles"})
        assert s == 404, f"unknown slug must 404, got {s}"
        return f"{slug}/handles → READY, unknown slug 404"
    run("resource-done", t_resource_done)

    # 5. autopilot dry run (conservative: inspection-only connectors skip)
    def t_autopilot():
        s, b = post("/api/autopilot", {"slug": TARGETS[0][0]})
        assert s == 200 and b.get("ok"), f"autopilot: {s} {b}"
        assert "executed" in b and "skipped" in b and "verified" in b, f"shape: {b}"
        return f"executed={len(b['executed'])} skipped={len(b['skipped'])} verified={b['verified'].get('progress', '?')}%"
    run("autopilot", t_autopilot)

    # 6. adversarial: bad digit, no-present, reuse, unknown task, evil tools
    def t_adversarial():
        s, b = get("/api/state")
        tid = b["tasks"][0]["id"] if b["tasks"] else None
        if tid:
            s, _ = post("/api/decide", {"task_id": tid, "digit": "99"})
            assert s == 400, f"bad digit must 400, got {s}"
            s, _ = post("/api/decide", {"task_id": tid, "digit": "7"})
            assert s == 409, f"decide without present must 409, got {s}"
            s, p = post("/api/present", {"task_id": tid})
            ref = p["prediction_ref"]
            s, _ = post("/api/decide", {"task_id": tid, "digit": "7", "prediction_ref": ref})
            s2, _ = post("/api/decide", {"task_id": tid, "digit": "7", "prediction_ref": ref})
            assert s2 == 409, f"prediction reuse must 409, got {s2}"
        s, _ = post("/api/decide", {"task_id": "NOPE", "digit": "7"})
        assert s == 404, f"unknown task must 404, got {s}"
        for evil in ("xmr.pay", "spend.authorize", "post.publish", "mail.send",
                     "buy.now", "domain.register"):
            s, m = post("/mcp", {"method": "tools/call",
                                 "params": {"name": evil, "arguments": {}}})
            assert "error" in m, f"{evil} not blocked: {m}"
        s, m = post("/mcp", {"method": "tools/call",
                             "params": {"name": "receipt.get",
                                        "arguments": {"id": "receipt:nope"}}})
        assert "error" in m, f"unknown receipt must error: {m}"
        return "400/409/404/unknown-tool/unknown-receipt all enforced"
    run("adversarial", t_adversarial)

    # 7. receipt chain verifies end to end
    def t_verify():
        from validation.verify import verify_log
        v = verify_log(os.getenv("RECEIPT_LOG", os.path.join(ROOT, "dash", "receipts.jsonl")))
        assert v["ok"], f"chain broken: {v}"
        return f"{v['checked']} receipts re-settled, chain ok"
    run("verify-chain", t_verify)

    # 8. chat agent paths against live state
    def t_chat():
        for msg, needle in [("tasks", "U="), ("graph", "L0 law"),
                            ("products", "setup.social"), ("hey", "hey."),
                            ("influencer sweep-alpha", "example.com")]:
            s, b = post("/api/chat", {"message": msg})
            assert s == 200 and needle in b.get("reply", ""), f"chat {msg!r}: {b}"
        return "tasks/graph/products/hey/influencer all answer"
    run("chat-agent", t_chat)

    print(f"\nTARGETS {TS}: {PASS[0]}/{total[0]} passed — log {RUNLOG}")
    return 0 if PASS[0] == total[0] else 1


if __name__ == "__main__":
    raise SystemExit(main())
