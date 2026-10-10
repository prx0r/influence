"""Pack loader — read + validate oddhobbies listing packs.

Packs are source of truth. Compilers never invent values.
"""
from __future__ import annotations

import json
import os

PACKS_DIR = os.getenv("ODDHOBBIES_PACKS", "/root/oddhobbies/stores")

REQUIRED = ("sku", "store_id", "price")
WARN_IF_MISSING = ("etsy_title", "tags", "description", "taxonomy_id")


def pack_path(store_id: str, sku: str) -> str:
    return os.path.join(PACKS_DIR, store_id, "listings", f"{sku}.json")


def load(store_id: str, sku: str) -> dict:
    with open(pack_path(store_id, sku)) as f:
        return json.load(f)


def validate(pack: dict) -> list[str]:
    """Returns list of gaps. Empty = valid. Missing REQUIRED = fail."""
    gaps = []
    for k in REQUIRED:
        if pack.get(k) in (None, ""):
            gaps.append(f"missing required: {k}")
    for k in WARN_IF_MISSING:
        if not pack.get(k):
            gaps.append(f"warn: missing {k}")
    tags = pack.get("tags") or []
    if tags and (len(tags) > 13 or any(len(t) > 20 for t in tags)):
        gaps.append(f"warn: tags need Etsy normalization ({len(tags)} tags)")
    return gaps


def list_packs(store_id: str = "oddhobb") -> list[dict]:
    d = os.path.join(PACKS_DIR, store_id, "listings")
    if not os.path.isdir(d):
        return []
    out = []
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json"):
            continue
        try:
            with open(os.path.join(d, fn)) as f:
                p = json.load(f)
            out.append({
                "sku": p.get("sku", fn[:-5]),
                "title": (p.get("etsy_title") or "")[:60],
                "price": p.get("price"),
                "state": p.get("state"),
                "etsy_listing_id": p.get("etsy_listing_id"),
                "gaps": len(validate(p)),
            })
        except (OSError, ValueError):
            continue
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", nargs="?", const="oddhobb", default=None)
    ap.add_argument("--show", nargs=2, metavar=("STORE", "SKU"), default=None)
    args = ap.parse_args()
    if args.list:
        for p in list_packs(args.list):
            print(f"{p['sku']:30} ${p['price']!s:>7} {p['state']:8} gaps={p['gaps']} {p['title'][:50]}")
    if args.show:
        p = load(*args.show)
        print(json.dumps({k: v for k, v in p.items() if k != "description"}, indent=1)[:2000])
        print("GAPS:", validate(p))
