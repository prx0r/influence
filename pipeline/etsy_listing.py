"""LEGACY agent function (old oddhobbies packs).

Use pipeline/runner.py (catalog packs + ChannelRelease + effect tasks)
for all new work. This module remains for migration compat only.

Agent function: etsy.listing — 'add this product to Etsy'.

One call takes a SKU through the whole flow:
  pack → template → compile → preview → human task → (approval) → push
  → images → verify → receipt.

The agent calls preview(sku) to show the human what will happen.
The human approves the task. The agent (or runner) calls execute(task_id).
Nothing publishes without approval. Everything receipts.
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
try:
    from compilers.pack_loader import load, validate
    from compilers.template import build_description, image_checklist, coherence_check
    from compilers.etsy import compile_etsy
    from actions import log_action
    from gates.human_confirm import create_task
except ImportError:
    from pipeline.compilers.pack_loader import load, validate
    from pipeline.compilers.template import build_description, image_checklist, coherence_check
    from pipeline.compilers.etsy import compile_etsy
    from pipeline.actions import log_action
    from pipeline.gates.human_confirm import create_task


def preview(store_id: str, sku: str, specs_block: str = "",
            shipping_block: str = "") -> dict:
    """Full preview of what 'add to Etsy' would do. No side effects."""
    pack = load(store_id, sku)
    gaps = validate(pack)
    description, desc_warnings = build_description(pack, specs_block, shipping_block)

    # compile against templated description (not raw pack desc)
    pack_for_compile = dict(pack)
    pack_for_compile["description"] = description
    compiled = compile_etsy(pack_for_compile)

    images = image_checklist(pack)
    coherence = coherence_check(pack, description)

    return {
        "sku": sku, "store": store_id,
        "pack_gaps": gaps,
        "listing_id": pack.get("etsy_listing_id"),
        "live_state": pack.get("state"),
        "payload_fields": sorted(compiled["payload"].keys()),
        "payload_warnings": compiled["warnings"] + desc_warnings,
        "description_chars": len(description),
        "description_preview": description[:500],
        "images": images,
        "coherence": coherence,
        "price": pack.get("price"),
        "ready": not images["missing_required"] and not coherence,
    }


def request_push(store_id: str, sku: str, specs_block: str = "",
                 shipping_block: str = "", campaign: str | None = None) -> dict:
    """Create the human approval task. Returns task for the agent to show."""
    pv = preview(store_id, sku, specs_block, shipping_block)
    pack = load(store_id, sku)
    task = create_task(
        action="etsy_push",
        payload={
            "channel": "etsy",
            "sku": sku,
            "store": store_id,
            "listing_id": pv["listing_id"],
            "title": (pack.get("etsy_title") or "")[:80],
            "price": pack.get("price"),
            "fields": pv["payload_fields"],
            "images": pv["images"]["score"],
            "coherence": pv["coherence"],
            "campaign": campaign,
            "specs_block": specs_block,
            "shipping_block": shipping_block,
        },
        urgency="medium",
        slug=pack.get("brand_id", store_id),
    )
    log_action("etsy", f"push requested {sku} (task {task['task_id']})", 0.0,
               sku, campaign, pack.get("brand_id", store_id),
               str(pv["listing_id"] or ""), 0, 0, None, "UNKNOWN")
    return {"task": task, "preview": pv}


def execute(task_id: int, dry_run: bool = True) -> dict:
    """Run an approved push via effect task + ReviewBundle. (dirs 16, 17)

    Dir 16: approval binds the frozen payload hash. This function NEVER
    parses prose to recover what was approved and NEVER recompiles.
    It loads the effect task, checks state == APPROVED, loads the
    ReviewBundle payload by hash, verifies bytes match, then executes
    through runtime.execute with the task's grant.

    Dir 17: APPROVED = permission to attempt. Only the receipt closes
    the task (transition to VERIFYING → PROVEN_TRUE/FALSE here).
    """
    try:
        from effects import get_task, get_bundle, transition
    except ImportError:
        from pipeline.effects import get_task, get_bundle, transition
    try:
        from adapters.etsy import push_listing
        from runtime import make_spec, execute as _exec
    except ImportError:
        from pipeline.adapters.etsy import push_listing
        from pipeline.runtime import make_spec, execute as _exec

    t = get_task(task_id)
    if not t:
        return {"ok": False, "reason": f"unknown effect task {task_id}"}
    if t["state"] != "APPROVED":
        return {"ok": False,
                "reason": f"task {task_id} is {t['state']}, not APPROVED",
                "next": "human must approve the exact revision first"}
    b = get_bundle(t["review_bundle_id"])
    if not b:
        return {"ok": False, "reason": "review bundle missing"}
    if b["payload_hash"] != t["payload_hash"]:
        return {"ok": False,
                "reason": "payload drift since approval: re-review required"}
    payload = b["payload"]
    listing_id = str((b.get("consequence") or {}).get("target", "")
                     ).replace("listing:", "")
    if not listing_id:
        return {"ok": False, "reason": "bundle has no listing target"}

    if dry_run:
        return {"ok": True, "dry_run": True, "task_id": task_id,
                "payload_hash": t["payload_hash"][:16],
                "fields": sorted(payload.keys())}

    # grant from task (minted at approval time, bound to payload hash)
    grant = {"payload_hash": t["payload_hash"],
             "expires_at": 9999999999,  # replaced by real grant minting
             "action": "etsy.listing.update"}
    spec = make_spec(t["brand"], "etsy.listing.update", "listing_mutate",
                     "pipeline.adapters.etsy:push_listing",
                     f"listing:{listing_id}", payload,
                     campaign=b.get("campaign"),
                     expected_cost_usd=b.get("cost_estimate_usd", 0.0))
    transition(task_id, "GRANTED", by="runtime")
    transition(task_id, "EXECUTING")
    result = _exec(spec, grant, lambda: push_listing(
        listing_id, payload, b.get("sku", ""),
        campaign=b.get("campaign"), dry_run=False,
        ctx={"grant": grant, "spec_id": spec["id"]}))
    transition(task_id, "VERIFYING")
    if result.get("ok"):
        transition(task_id, "PROVEN_TRUE", receipt_id=result.get("receipt", {}).get("id")
                   if isinstance(result.get("receipt"), dict) else None)
    else:
        transition(task_id, "PROVEN_FALSE")
    return {**result, "task_id": task_id}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", nargs=2, metavar=("STORE", "SKU"), default=None)
    ap.add_argument("--request", nargs=2, metavar=("STORE", "SKU"), default=None)
    ap.add_argument("--execute", type=int, default=None)
    ap.add_argument("--campaign", default=None)
    args = ap.parse_args()
    if args.preview:
        print(json.dumps(preview(*args.preview), indent=1)[:2500])
    if args.request:
        r = request_push(*args.request, campaign=args.campaign)
        print(json.dumps({"task_id": r["task"]["task_id"], "title": r["task"]["title"],
                          "ready": r["preview"]["ready"],
                          "coherence": r["preview"]["coherence"],
                          "images": r["preview"]["images"]["score"]}, indent=1))
    if args.execute:
        print(json.dumps(execute(args.execute), indent=1)[:1500])
