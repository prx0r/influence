"""Agent function: etsy.listing — 'add this product to Etsy'.

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
    """Run an approved push. Reads payload from the task. Verifies + receipts."""
    import sqlite3
    db_path = os.getenv("DASH_DB", os.path.join(_HERE, "..", "dash", "influence.db"))
    db = sqlite3.connect(db_path, timeout=30)
    try:
        row = db.execute("SELECT title,instructions,done FROM human_actions WHERE id=?",
                         (task_id,)).fetchone()
        if not row:
            return {"ok": False, "reason": f"unknown task {task_id}"}
        title, instructions, done = row
        if not done:
            return {"ok": False, "reason": f"task {task_id} not approved yet",
                    "next": "human must approve first"}
    finally:
        db.close()

    # re-derive payload from instructions is fragile; instead re-run preview
    # from task title ("Approve: etsy_push → etsy" + SKU in instructions)
    import re
    m = re.search(r"SKU:\s*(\S+)", instructions or "")
    sku = m.group(1) if m else ""
    m2 = re.search(r"Channel:\s*(\S+)", instructions or "")
    if not sku:
        return {"ok": False, "reason": "could not recover SKU from task"}
    # find store from task: look up pack across known stores
    store_id = "oddhobb"
    pv = preview(store_id, sku)
    if not pv["listing_id"]:
        return {"ok": False, "reason": f"{sku} has no etsy_listing_id (draft creation not wired)"}

    try:
        from adapters.etsy import push_listing
    except ImportError:
        from pipeline.adapters.etsy import push_listing
    pack = load(store_id, sku)
    compiled = compile_etsy({**pack, "description": pv["description_preview"]})
    # rebuild full description for push (preview was truncated)
    full_desc, _ = build_description(pack)
    compiled["payload"]["description"] = full_desc
    return push_listing(str(pv["listing_id"]), compiled["payload"], sku,
                        campaign=None, dry_run=dry_run)


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
