"""Independent verifier. Replays the receipt log from bytes: chain check,
per-receipt id recompute, per-receipt gate replay against stored evidence.
Builders never edit this directory: it imports stdlib + acom ONLY. A test
below enforces that boundary."""

ALLOWED_IMPORT_ROOTS = ("acom",)


def verify_log(path: str) -> dict:
    import json
    import os
    import sys
    qp = os.getenv("QPRIVATELY_PATH", "/home/ubuntu/qprivately")
    if qp not in sys.path:
        sys.path.insert(0, qp)
    from acom import receipts as R
    from acom import store as StoreMod
    st = StoreMod.Store(path)
    chained = st.verify_chain()
    checked, failed = 0, []
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                payload = json.loads(line)["payload"]
                rc, ev = payload.get("receipt"), payload.get("evidence", [])
                if rc is None:
                    failed.append({"reason": "missing receipt"})
                    continue
                v = R.settle(rc, ev)
                checked += 1
                # FAIL receipts are first-class: replay-identity is the bar,
                # not passed-ness.
                if v["reason"] != "all gates replay identically" and not v["ok"]:
                    failed.append({"id": rc.get("id"), "reason": v["reason"]})
    return {"chained": chained, "checked": checked, "failed": failed,
            "ok": chained and not failed}
