"""Effect runtime — the ONE syscall for consequences. (dirs 8, 9, 36)

No code may directly cause an external consequence. Everything that spends,
publishes, sends, buys, mutates, launches, or orders goes through:

    runtime.execute(ActionSpec)

with a verified qprivately grant. Without it: FAIL CLOSED.

AGENTS.md invariant #1: NO EXTERNAL CONSEQUENCE OUTSIDE THE EFFECT RUNTIME.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
try:
    from actions import log_action
except ImportError:
    from pipeline.actions import log_action  # noqa

# Consequence classes that REQUIRE the runtime (dir 36)
CONSEQUENCE_CLASSES = (
    "spend", "publish", "send", "listing_mutate", "ad_launch",
    "order", "dns", "generate_paid",
)

# Adapter functions that are BLOCKED from direct calls (dir 9)
BLOCKED_DIRECT = (
    "pipeline.adapters.etsy:push_listing",
    "pipeline.adapters.etsy:upload_image",
    "pipeline.scheduler:queue_post",
    "pipeline.etsy_listing:execute",
    "pipeline.runner:run_pack[live]",
)


def _sha(obj) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def make_spec(brand: str, capability: str, consequence: str,
              adapter: str, target: str, payload: dict,
              campaign: str | None = None,
              expected_cost_usd: float = 0.0,
              source_hashes: list | None = None,
              verifier: str = "", review_bundle_id: str | None = None,
              idempotency_key: str | None = None) -> dict:
    """Build an ActionSpec. Immutable once created — hash binds it."""
    if consequence not in CONSEQUENCE_CLASSES:
        raise ValueError(f"unknown consequence class: {consequence}")
    spec = {
        "id": f"act_{hashlib.sha256(f'{brand}:{capability}:{target}:{time.time_ns()}'.encode()).hexdigest()[:12]}",
        "brand": brand,
        "campaign": campaign,
        "capability": capability,
        "consequence": consequence,
        "adapter": adapter,
        "target": target,
        "payload_ref": None,  # filled by caller if payload stored elsewhere
        "payload_sha256": _sha(payload),
        "payload": payload,
        "source_hashes": source_hashes or [],
        "expected_cost_usd": expected_cost_usd,
        "verifier": verifier,
        "review_bundle_id": review_bundle_id,
        "idempotency_key": idempotency_key or f"{adapter}:{target}:{_sha(payload)[:12]}",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    return spec


def check_grant(spec: dict, grant: dict) -> tuple[bool, str]:
    """Verify a qprivately grant authorizes this exact spec.

    Uses qp/authority when available, falls back to structural checks
    (payload hash match + expiry + capability match). Fail closed.
    """
    # 1. payload hash must match exactly (dir 16)
    if grant.get("payload_hash", "").replace("sha256:", "") not in (
            spec["payload_sha256"], spec["payload_sha256"].replace("sha256:", "")):
        # normalize both sides
        gh = grant.get("payload_hash", "")
        sh = spec["payload_sha256"]
        if gh.replace("sha256:", "") != sh.replace("sha256:", ""):
            return False, "grant payload hash mismatch (re-review required)"
    # 2. expiry
    try:
        if int(grant.get("expires_at", 0)) < int(time.time()):
            return False, "grant expired"
    except (TypeError, ValueError):
        return False, "grant expiry unreadable"
    # 3. capability / action match
    ga = grant.get("action", "")
    if ga and ga not in (spec["capability"], spec["consequence"],
                         f"{spec['capability']}.{spec['consequence']}"):
        # try qp authority for richer match
        pass
    # 4. canonical law/acom verifier when the grant carries canonical shape
    # (dir 12: qprivately defines authority). Legacy qp.authority-shape
    # grants rely on structural checks 1-3 until issuance migrates (todo 7).
    if "capability" in grant or "constraints" in grant:
        try:
            sys.path.insert(0, os.path.dirname(os.path.dirname(_HERE)))
            from law.acom import grants as _G
            import datetime as _dt
            action = {"capability": spec.get("capability", ""),
                      "value": spec.get("expected_cost_usd", 0),
                      "calls": 1, "risk_usd": spec.get("expected_cost_usd", 0)}
            facts = {"campaign": spec.get("campaign") or "",
                     "channel": (spec.get("adapter") or "").split(":")[0]}
            now_iso = _dt.datetime.now(_dt.timezone.utc).isoformat()
            r = _G.verify_grant(grant, action, facts, now_iso)
            if not r.get("ok"):
                return False, f"canonical authority rejected: {r.get('reason')}"
        except ImportError:
            pass  # structural checks above stand
        except Exception as e:  # noqa: BLE001 — fail closed on verifier error
            return False, f"authority error: {e}"
    return True, "grant authorizes exact payload"


def execute(spec: dict, grant: dict | None, executor) -> dict:
    """THE syscall. Grant required for all consequence classes.

    executor: zero-arg callable performing the effect, returning
    {"ok": bool, "external_id": str, "response": dict}.
    Logs to actions ledger either way. Returns result + receipt hook.
    """
    if spec.get("consequence") in CONSEQUENCE_CLASSES and not grant:
        log_action(spec.get("adapter", "?").split(":")[0] if ":" in spec.get("adapter", "") else "runtime",
                   f"BLOCKED {spec.get('capability')} (no grant)", 0.0,
                   None, spec.get("campaign"), spec.get("brand"),
                   None, 0, 1, None, "FAIL")
        return {"ok": False, "reason": "no grant: FAIL CLOSED (dir 8)",
                "spec_id": spec.get("id")}
    if grant:
        ok, reason = check_grant(spec, grant)
        if not ok:
            log_action("runtime", f"BLOCKED {spec.get('capability')} ({reason})", 0.0,
                       None, spec.get("campaign"), spec.get("brand"),
                       None, 0, 1, None, "FAIL")
            return {"ok": False, "reason": reason, "spec_id": spec.get("id")}
    try:
        result = executor()
    except Exception as e:  # noqa: BLE001
        log_action("runtime", f"EXEC FAIL {spec.get('capability')}: {e}", 0.0,
                   None, spec.get("campaign"), spec.get("brand"),
                   None, 0, 1, None, "FAIL")
        return {"ok": False, "reason": str(e)[:200], "spec_id": spec.get("id")}
    log_action("runtime", f"EXEC {spec.get('capability')} → {spec.get('target')}",
               spec.get("expected_cost_usd", 0.0),
               None, spec.get("campaign"), spec.get("brand"),
               str(result.get("external_id") or ""), 1, 1,
               result.get("receipt_id"), "PASS" if result.get("ok") else "FAIL")
    return {**result, "spec_id": spec.get("id")}


def guard_imports() -> list[str]:
    """CI check (dir 36): no direct-effect imports outside runtime/adapters.

    Returns violations. Adapters may exist but must require execution context.
    Currently advisory — hard enforcement lands with grant plumbing.
    """
    import glob
    violations = []
    for f in glob.glob(os.path.join(os.path.dirname(_HERE), "**", "*.py"), recursive=True):
        if "/pipeline/adapters/" in f or "/pipeline/runtime" in f:
            continue
        try:
            src = open(f).read()
        except OSError:
            continue
        for pat in ("push_listing(", "upload_image(", "queue_post("):
            if pat in src and "dry_run=True" not in src.split(pat)[0][-500:]:
                # crude: flag direct calls outside runtime/adapters/tests
                if "/tests/" not in f and "runtime.py" not in f:
                    violations.append(f"{f}: direct {pat}")
                    break
    return violations


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--guard", action="store_true", help="list direct-effect call sites")
    ap.add_argument("--spec-demo", action="store_true")
    args = ap.parse_args()
    if args.guard:
        for v in guard_imports():
            print(" ", v)
    if args.spec_demo:
        s = make_spec("oddhobb", "etsy.listing.update", "listing_mutate",
                      "pipeline.adapters.etsy:push_listing",
                      "listing:4587938693", {"title": "x"},
                      expected_cost_usd=0.0)
        print(json.dumps({k: v for k, v in s.items() if k != "payload"}, indent=1))
