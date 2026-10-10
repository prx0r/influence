"""Campaign runner — one pack → all channels, dry-run default.

Compile everything, gate everything, push nothing without approval.
End-to-end receipt per channel. This is the MVP loop.
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
try:
    from compilers.pack_loader import load, validate
    from compilers.etsy import compile_etsy
    from compilers.amazon import compile_amazon
    from compilers.social import compile_all as compile_social
    from compilers.pin import compile_pin
    from actions import log_action
    from campaign import create as campaign_create, add_item, get_campaign
except ImportError:
    from pipeline.compilers.pack_loader import load, validate
    from pipeline.compilers.etsy import compile_etsy
    from pipeline.compilers.amazon import compile_amazon
    from pipeline.compilers.social import compile_all as compile_social
    from pipeline.compilers.pin import compile_pin
    from pipeline.actions import log_action
    from pipeline.campaign import create as campaign_create, add_item, get_campaign

CHANNELS = ("etsy", "amazon", "pinterest", "x", "instagram", "tiktok", "youtube")


def run_pack(store_id: str, sku: str, campaign_name: str | None = None,
             channels: tuple = CHANNELS, dry_run: bool = True,
             shop_url: str = "", brand_tags: list | None = None,
             handles: dict | None = None) -> dict:
    """Compile one pack for all channels. Push only with dry_run=False + approval."""
    pack = load(store_id, sku)
    gaps = validate(pack)
    out: dict = {"sku": sku, "store": store_id, "gaps": gaps,
                 "dry_run": dry_run, "channels": {}}

    # campaign
    camp_id = None
    if campaign_name:
        camp_id = campaign_create(campaign_name, pack.get("brand_id", store_id))
        out["campaign_id"] = camp_id

    # etsy
    if "etsy" in channels:
        c = compile_etsy(pack)
        ch: dict = {"compiled": sorted(c["payload"].keys()), "warnings": c["warnings"]}
        if camp_id:
            add_item(camp_id, sku, "etsy", c["payload"])
        if not dry_run:
            try:
                from adapters.etsy import push_listing
            except ImportError:
                from pipeline.adapters.etsy import push_listing
            lid = str(pack.get("etsy_listing_id", ""))
            if lid and lid != "None":
                ch["push"] = push_listing(lid, c["payload"], sku, campaign_name, dry_run=False)
            else:
                ch["push"] = {"ok": False, "reason": "no etsy_listing_id (draft creation not yet wired)"}
        out["channels"]["etsy"] = ch

    # amazon
    if "amazon" in channels:
        c = compile_amazon(pack)
        out["channels"]["amazon"] = {
            "title": c["title"][:80], "bullets_n": len(c["bullets"]),
            "terms_len": len(c["search_terms"]), "warnings": c["warnings"],
            "tsv_fields": len(c["tsv_row"]),
        }
        if camp_id:
            add_item(camp_id, sku, "amazon", {"title": c["title"]})

    # pinterest
    if "pinterest" in channels:
        c = compile_pin(pack, shop_url)
        out["channels"]["pinterest"] = {
            "title": c["title"][:60], "board": c["board"],
            "has_image": bool(c["image_url"]), "warnings": c["warnings"],
        }
        if camp_id:
            add_item(camp_id, sku, "pinterest", c)

    # social
    social_keys = [k for k in ("x", "instagram", "tiktok", "youtube") if k in channels]
    if social_keys:
        compiled = compile_social(pack, shop_url, brand_tags)
        for key in social_keys:
            c = compiled.get(key, {})
            text = c.get("text") or c.get("caption") or c.get("title") or ""
            ch = {"chars": len(text), "has_image": bool(c.get("image_url")),
                  "preview": text[:120]}
            if camp_id:
                add_item(camp_id, sku, key, {"preview": text[:200]})
            if not dry_run and handles and handles.get(key):
                try:
                    from scheduler import queue_post
                except ImportError:
                    from pipeline.scheduler import queue_post
                media = [c["image_url"]] if c.get("image_url") else []
                ch["queue"] = queue_post(key, handles[key], text, media,
                                         brand_slug=pack.get("brand_id", store_id),
                                         sku=sku, campaign=campaign_name)
            out["channels"][key] = ch

    log_action("campaign", f"run pack {sku} ({'dry' if dry_run else 'LIVE'})", 0.0,
               sku, campaign_name, pack.get("brand_id", store_id),
               None, 1, 1, None, "PASS")
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("sku", help="e.g. KEYCHAIN-PET")
    ap.add_argument("--store", default="oddhobb")
    ap.add_argument("--campaign", default=None)
    ap.add_argument("--live", action="store_true",
                    help="PUSH for real (requires human approval first!)")
    ap.add_argument("--channels", default=",".join(CHANNELS))
    args = ap.parse_args()
    r = run_pack(args.store, args.sku, args.campaign,
                 tuple(args.channels.split(",")), dry_run=not args.live)
    print(json.dumps(r, indent=1)[:3000])
