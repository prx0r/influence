"""Catalog reader — pogpet/catalog/packs is canonical product truth.

Influence READS packs. Never writes, never redefines, never duplicates.
Pack controls what may be claimed. Influence controls how claims are expressed.

Levels gate marketing permission (dir 29):
  DRAFT       → inspect only
  PRINT_READY → internal test content only
  LISTABLE    → listings + organic content
  PROVEN      → paid ads + scale + bundles
  RETIRED     → block all new publishing
"""
from __future__ import annotations

import hashlib
import json
import os

CATALOG = os.getenv("POGPET_CATALOG", "/root/pogpet/catalog/packs")
GRAPH_PATH = os.getenv("POGPET_GRAPH", "/root/pogpet/catalog/graph.json")

# Generic scale references (rendering helpers, NOT product facts).
# Real-world objects with true dimensions for prompt grounding.
# Product dims NEVER live here — only in catalog packs.
REFERENCES = {
    "gb_10p": {"label": "UK 10p coin", "dia_mm": 24.5, "use": "small objects"},
    "gb_1": {"label": "UK £1 coin (12-sided)", "dia_mm": 23.4, "use": "small objects"},
    "us_quarter": {"label": "US quarter", "dia_mm": 24.3, "use": "small objects"},
    "croc_hole": {"label": "Croc shoe hole", "dia_mm": 13.0, "use": "jibbit fit"},
    "pint_glass": {"label": "UK pint glass", "height_mm": 150, "dia_mm": 80, "use": "desk/shelf context"},
    "paperback": {"label": "Paperback book", "height_mm": 198, "width_mm": 129, "use": "shelf context"},
    "tv_remote": {"label": "TV remote", "length_mm": 200, "use": "desk context"},
    "a4": {"label": "A4 sheet", "width_mm": 210, "height_mm": 297, "use": "flat products"},
    "credit_card": {"label": "Credit card", "width_mm": 85.6, "height_mm": 54.0, "use": "cards, tags"},
    "dartboard": {"label": "Bristle dartboard", "dia_mm": 451, "use": "dart context"},
    "dart": {"label": "Steel-tip dart", "length_mm": 150, "use": "dart context"},
    "mug": {"label": "Standard mug", "height_mm": 95, "dia_mm": 80, "use": "desk/kitchen context"},
    "fingertip": {"label": "Adult fingertip", "width_mm": 15, "use": "macro scale"},
}


# Marketing permission per pack level (dir 29)
PERMISSIONS = {
    "DRAFT": ("inspect",),
    "PRINT_READY": ("inspect", "test_content"),
    "LISTABLE": ("inspect", "test_content", "listing", "organic"),
    "PROVEN": ("inspect", "test_content", "listing", "organic", "paid", "bundle", "scale"),
    "RETIRED": (),
}


def _hash(obj) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def pack_path(sku: str) -> str:
    return os.path.join(CATALOG, sku, "product.json")


def load(sku: str) -> dict:
    with open(pack_path(sku)) as f:
        return json.load(f)


def gates(sku: str) -> dict:
    with open(os.path.join(CATALOG, sku, "gates.json")) as f:
        return json.load(f)


def level(sku: str) -> str:
    try:
        return gates(sku).get("level", "DRAFT")
    except (OSError, ValueError):
        return "DRAFT"


def may(sku: str, action: str) -> bool:
    """Marketing permission check. action: listing|organic|paid|bundle|scale|test_content|inspect."""
    return action in PERMISSIONS.get(level(sku), ())


def pack_hash(sku: str) -> str:
    return _hash(load(sku))


def physical_truth(sku: str) -> dict:
    """What may be claimed. Facts only, no marketing."""
    p = load(sku)
    g = p.get("geometry", {})
    m = p.get("manufacture", {})
    c = p.get("cost", {})
    dims = g.get("dims_mm") or []
    return {
        "sku": sku,
        "name": p.get("name", ""),
        "dims_mm": dims,
        "material": m.get("material", ""),
        "process": m.get("process", ""),
        "supplier": m.get("supplier", ""),
        "finish": m.get("finish", ""),
        "lead_build_days": (m.get("lead_time_days") or {}).get("build"),
        "lead_ship_min": (m.get("lead_time_days") or {}).get("ship_min"),
        "lead_ship_max": (m.get("lead_time_days") or {}).get("ship_max"),
        "cost_print": (c.get("print") or {}).get("amount"),
        "cost_shipping": (c.get("shipping") or {}).get("amount"),
        "cost_currency": c.get("currency", "USD"),
        "price": ((p.get("listing") or {}).get("price") or {}).get("amount"),
        "price_currency": ((p.get("listing") or {}).get("price") or {}).get("currency", "USD"),
        "approved_claims": p.get("approved_claims", []),
        "forbidden_claims": p.get("forbidden_claims", []),
        "audience": p.get("audience", {}),
        "slots": p.get("slots", []),
        "level": level(sku),
        "pack_hash": pack_hash(sku),
    }


def listing_images(sku: str) -> list[dict]:
    """Canonical listing images with sha256 (render-of-print-file)."""
    try:
        with open(os.path.join(CATALOG, sku, "listing", "renders.json")) as f:
            r = json.load(f)
    except (OSError, ValueError):
        return []
    base = os.path.join(CATALOG, sku, "listing")
    return [{"file": fn, "path": os.path.join(base, fn),
             "sha256": meta.get("sha256", ""), "source": meta.get("source", "")}
            for fn, meta in (r.get("images") or {}).items()]


def list_packs(level_filter: str | None = None) -> list[dict]:
    if not os.path.isdir(CATALOG):
        return []
    out = []
    for sku in sorted(os.listdir(CATALOG)):
        if not os.path.isfile(pack_path(sku)):
            continue
        try:
            p = load(sku)
            lv = level(sku)
        except (OSError, ValueError):
            continue
        if level_filter and lv != level_filter:
            continue
        listing = p.get("listing") or {}
        out.append({
            "sku": sku,
            "name": p.get("name", "")[:60],
            "level": lv,
            "price": (listing.get("price") or {}).get("amount"),
            "permissions": list(PERMISSIONS.get(lv, ())),
            "pack_hash": pack_hash(sku)[:16],
        })
    return out


def gaps(sku: str) -> list[str]:
    """Missing truth that blocks marketing. Each gap → repair task, never guess."""
    p = load(sku)
    out = []
    g = p.get("geometry", {})
    if not g.get("dims_mm"):
        out.append(f"{sku}: no dims_mm (measure product / repair pack)")
    m = p.get("manufacture", {})
    if not m.get("material"):
        out.append(f"{sku}: no material")
    if not m.get("supplier"):
        out.append(f"{sku}: no supplier")
    listing = p.get("listing") or {}
    if (listing.get("price") or {}).get("amount") in (None, 0):
        out.append(f"{sku}: no approved price (pricing policy required)")
    if not listing_images(sku):
        out.append(f"{sku}: no canonical listing images")
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--level", default=None)
    ap.add_argument("--truth", default=None, metavar="SKU")
    ap.add_argument("--gaps", default=None, metavar="SKU")
    ap.add_argument("--images", default=None, metavar="SKU")
    args = ap.parse_args()
    if args.list:
        for p in list_packs(args.level):
            print(f"{p['sku']:25} {p['level']:12} ${str(p['price']):>8} {','.join(p['permissions'])}  {p['name'][:40]}")
    if args.truth:
        print(json.dumps(physical_truth(args.truth), indent=1))
    if args.gaps:
        for g in gaps(args.gaps):
            print(" ", g)
    if args.images:
        for im in listing_images(args.images):
            print(f"  {im['file']:30} {im['sha256'][:16]} {im['source']}")
