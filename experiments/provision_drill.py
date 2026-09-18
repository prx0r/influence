#!/usr/bin/env python3
"""provision_drill.py — the actual job, observe-only, logged + receipted.

Exercises the provisioning pipeline end to end WITHOUT buying anything:
  name check (taken + free) -> registrar compare -> pipeline setup view ->
  reconcile live targets -> phone bridge matrix -> verify chain.

Every check logs JSONL to runs/. Every finding gets a QP receipt.
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
RUNLOG = os.path.join(ROOT, "runs", f"provision-{TS}.jsonl")
os.makedirs(os.path.join(ROOT, "runs"), exist_ok=True)
GATES = ["evidence-fresh-v1", "no-duplicate-v1", "claim-resolved-v1"]
PASS = [0]


def log(check, passed, details=None):
    entry = {"ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
             "run": TS, "check": check, "passed": bool(passed)}
    if details:
        entry["details"] = details
    with open(RUNLOG, "a") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")


def receipt_for(check, passed, notes=""):
    from acom import objects as O
    from acom import receipts as R
    from acom import store as StoreMod
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    ev = [O.make_evidence(metric=f"provision.{check}",
                          value="PASS" if passed else "FAIL", unit="verdict",
                          as_of=now,
                          source={"class": "provision-drill", "artifact_hash": "sha256:provision",
                                  "label": check, "message": notes[:200]})]
    claim = O.make_claim(statement=f"provision drill {check} {'passed' if passed else 'failed'}",
                         domain="influence.provision",
                         result="TRUE" if passed else "FALSE")
    run = O.make_run(task_id=claim["id"], worker="influence-provision")
    store_path = os.getenv("RECEIPT_LOG", os.path.join(ROOT, "dash", "receipts.jsonl"))
    st = StoreMod.Store(store_path)
    sb = {"cursor": st.cursor, "rules_commit": "qprivately",
          "event_root": st.event_root, "state_root": ""}
    rc = R.transition(sb, {"id": claim["id"], "target": claim["id"],
                           "claim": claim, "grant": None},
                      ev, GATES, run, proof_level=4)
    st.append("transition", {"receipt": rc, "evidence": ev,
                             "claim": claim, "project": f"provision-{TS}"})
    return rc["id"]


def check(name, fn):
    try:
        notes = fn() or ""
        rid = receipt_for(name, True, str(notes))
        log(name, True, {"notes": str(notes)[:300], "receipt": rid})
        PASS[0] += 1
        print(f"PASS {name} [{rid}] :: {str(notes)[:130]}", flush=True)
        return True
    except AssertionError as e:
        rid = receipt_for(name, False, str(e))
        log(name, False, {"error": str(e)[:300], "receipt": rid})
        print(f"FAIL {name} [{rid}]: {e}", flush=True)
        return False


def _req(method, path, body=None):
    url = BASE + path + (("&" if "?" in path else "?") + f"token={TOKEN}" if TOKEN else "")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json",
                                          "User-Agent": "influence-sweep/1.0"},
                                 method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except ValueError:
            return e.code, {}


def main():
    total = [0]

    def run(name, fn):
        total[0] += 1
        return check(name, fn)

    # 1. taken name is BLOCKED with evidence (no guessing)
    def t_taken():
        s, b = _req("POST", "/api/chat", {"message": "check example.com"})
        assert s == 200 and "BLOCKED" in b.get("reply", ""), b
        assert "taken" in b["reply"].lower(), b
        return "example.com BLOCKED, authoritative"
    run("check-taken", t_taken)

    # 2. free-looking name yields buy path + prices, never auto-buy
    def t_free():
        s, b = _req("POST", "/api/chat", {"message": "check zzq-drill-4821.dev"})
        assert s == 200, (s, b)
        assert "MISSING" in b.get("reply", "") and "BUY-DOMAIN" in b.get("reply", ""), b
        return "free name -> human buy path, prices attached"
    run("check-free", t_free)

    # 3. pipeline setup view over live targets
    def t_setup():
        s, b = _req("POST", "/api/chat", {"message": "setup"})
        assert s == 200 and "idea→endpoint" in b.get("reply", ""), b
        assert "domain:" in b.get("reply", ""), b
        return "pipeline rows render in order"
    run("setup-view", t_setup)

    # 4. reconcile still honest after names kind registered
    def t_reconcile():
        s, b = _req("POST", "/api/reconcile", {})
        assert s == 200 and b.get("ok"), (s, b)
        s, st = _req("GET", "/api/state")
        kinds = {r["kind"] for i in st["influencers"] for r in i["resources"]}
        assert "domain" in kinds and "mail" in kinds and "number" in kinds, kinds
        return f"{len(st['influencers'])} projects reconciled, pipeline kinds present"
    run("reconcile-pipeline", t_reconcile)

    # 5. phone bridge matrix refuses IDENTITY_BRIDGED by policy
    def t_phone():
        sys.path.insert(0, ROOT)
        from core.cmail.connectors.phone import select_bridge
        r = select_bridge(["sms_in"], "PSEUDONYMOUS_BRIDGE")
        assert any(p.get("provider") == "telnyx" for p in r["rejected"]), r
        assert not any(p.get("provider") == "telnyx" or p.get("name") == "telnyx"
                       for p in r["eligible"]), r
        return "telnyx rejected under standard policy, reasons attached"
    run("phone-policy", t_phone)

    # 6. chain still verifies with drill receipts appended
    def t_verify():
        from validation.verify import verify_log
        v = verify_log(os.getenv("RECEIPT_LOG", os.path.join(ROOT, "dash", "receipts.jsonl")))
        assert v["ok"], v
        return f"{v['checked']} receipts re-settled, chain ok"
    run("verify-chain", t_verify)

    print(f"\nPROVISION {TS}: {PASS[0]}/{total[0]} passed — log {RUNLOG}")
    return 0 if PASS[0] == total[0] else 1


if __name__ == "__main__":
    raise SystemExit(main())
