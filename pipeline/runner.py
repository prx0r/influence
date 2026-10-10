"""Campaign runner — catalog SKU → ChannelRelease (dry-run compiles).

Dir 2: reads pogpet/catalog/packs ONLY. Old oddhobbies pack path retired
(kept as legacy import fallback, never primary).
Dir 9: NO live push path here. Publishing happens exclusively via effect
task (APPROVED) → runtime.execute → adapter. This module compiles and
creates draft releases + review bundles. Nothing else.
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
try:
    from catalog import load as catalog_load, level, may, pack_hash, listing_images
    from release import create as release_create, get as release_get, resolve_price
    from compilers.etsy import compile_catalog
    from compilers.template import build_catalog_description
    from effects import create_bundle, propose, transition
    from actions import log_action
except ImportError:
    from pipeline.catalog import load as catalog_load, level, may, pack_hash, listing_images
    from pipeline.release import create as release_create, get as release_get, resolve_price
    from pipeline.compilers.etsy import compile_catalog
    from pipeline.compilers.template import build_catalog_description
    from pipeline.effects import create_bundle, propose, transition
    from pipeline.actions import log_action


def preview_pack(sku: str, brand: str = "oddhobb",
                 channel: str = "etsy") -> dict:
    """Pure dry-run: compile + validate, zero DB writes. Safe for GET."""
    lv = level(sku)
    if channel in ("etsy", "shopify", "pinterest", "x", "instagram",
                   "tiktok", "youtube") and not may(sku, "listing"):
        return {"ok": False, "sku": sku, "level": lv,
                "reason": f"{sku} is {lv}: {channel} requires LISTABLE+"}
    if channel == "etsy":
        c = compile_catalog(sku)
        payload, warnings = c["payload"], c["warnings"]
    else:
        return {"ok": False, "reason": f"channel compiler for {channel} not yet ported"}
    media = [{"file": im["file"], "sha256": im["sha256"][:16]}
             for im in listing_images(sku)]
    pr = resolve_price(sku)
    return {"ok": True, "sku": sku, "level": lv,
            "payload_fields": sorted(payload.keys()),
            "payload_preview": {k: (str(v)[:200]) for k, v in payload.items()},
            "media": media, "price": pr, "warnings": warnings,
            "dry_run": True}


def run_pack(sku: str, brand: str = "oddhobb", channel: str = "etsy",
             campaign: str | None = None) -> dict:
    """Compile one catalog SKU into a draft ChannelRelease + ReviewBundle.

    Returns release + bundle + human task. Never pushes. Publishing is a
    separate step: approve task → runtime.execute → adapter → verify.
    """
    # 1. pack level permission (dir 29)
    lv = level(sku)
    if channel in ("etsy", "shopify", "pinterest", "x", "instagram",
                   "tiktok", "youtube") and not may(sku, "listing"):
        return {"ok": False, "sku": sku, "level": lv,
                "reason": f"{sku} is {lv}: {channel} requires LISTABLE+"}
    # 2. compile
    if channel == "etsy":
        c = compile_catalog(sku)
        payload, warnings = c["payload"], c["warnings"]
    else:
        return {"ok": False, "reason": f"channel compiler for {channel} not yet ported"}
    # 3. price truth (dir 7) — enforced inside release.create
    media = [{"file": im["file"], "sha256": im["sha256"][:16]}
             for im in listing_images(sku)]
    try:
        rel = release_create(brand, channel, sku, payload, media,
                             campaign=campaign, compiler="etsy-v1",
                             compiler_version="2-catalog")
    except ValueError as e:
        return {"ok": False, "sku": sku, "reason": str(e)}
    # 4. review bundle (immutable, what the human approves)
    b = create_bundle(f"{channel}_listing", brand, payload,
                      campaign=campaign, sku=sku,
                      source_refs={"pack": sku, "pack_hash": rel["pack_hash"]},
                      artifacts=[{"kind": "image", "id": m["file"]} for m in media],
                      cost_estimate_usd=0.0,
                      consequence={"capability": f"{channel}.listing.update",
                                   "target": f"{channel}:{sku}"})
    # 5. effect task (PROPOSED — human moves to REVIEW_READY → APPROVED)
    t = propose(brand, f"{channel}.listing.update", b["id"],
                risk_class="medium")
    log_action(channel, f"release drafted {sku} ({rel['id']})", 0.0,
               sku, campaign, brand, None, 1, 1, None, "PASS")
    return {"ok": True, "sku": sku, "level": lv,
            "release_id": rel["id"], "payload_hash": rel["payload_hash"],
            "bundle_id": b["id"], "task_id": t["task_id"],
            "price": rel["price"], "warnings": warnings,
            "next": f"review bundle {b['id']}, approve task {t['task_id']}"}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("sku", help="catalog SKU e.g. CHARM-CROC-PET")
    ap.add_argument("--brand", default="oddhobb")
    ap.add_argument("--channel", default="etsy")
    ap.add_argument("--campaign", default=None)
    args = ap.parse_args()
    print(json.dumps(run_pack(args.sku, args.brand, args.channel,
                              args.campaign), indent=1)[:2500])
