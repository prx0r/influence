"""Etsy compiler — pack → Etsy PATCH payload.

Proven pattern (Halloween/Xmas cards, Oct 2026). Normalizes title/tags/
materials/taxonomy. Never invents values — everything from the pack.
"""
from __future__ import annotations

TITLE_MAX = 140
TAGS_MAX = 13
TAG_MAX_LEN = 20


def normalize_tags(tags: list[str]) -> list[str]:
    """Dedupe, lowercase-compare, truncate to 13×20. No invention."""
    seen: set[str] = set()
    out: list[str] = []
    for t in tags or []:
        t = str(t).strip()
        if not t or t.lower() in seen:
            continue
        if len(t) > TAG_MAX_LEN:
            continue  # drop overlong rather than mangle
        seen.add(t.lower())
        out.append(t)
        if len(out) >= TAGS_MAX:
            break
    return out


def compile_etsy(pack: dict) -> dict:
    """Pack → PATCH body. Returns {payload, warnings}."""
    warnings: list[str] = []
    payload: dict = {}

    title = (pack.get("etsy_title") or "").strip()
    if len(title) > TITLE_MAX:
        warnings.append(f"title {len(title)} chars > {TITLE_MAX}, truncating")
        title = title[:TITLE_MAX].rsplit(" ", 1)[0]
    if title:
        payload["title"] = title

    desc = (pack.get("description") or "").strip()
    if desc:
        payload["description"] = desc
    else:
        warnings.append("no description — PATCH will skip")

    tags = normalize_tags(pack.get("tags") or [])
    if tags:
        payload["tags"] = tags
    if len(pack.get("tags") or []) != len(tags):
        warnings.append(f"tags normalized {len(pack.get('tags') or [])} → {len(tags)}")

    if pack.get("taxonomy_id"):
        payload["taxonomy_id"] = pack["taxonomy_id"]

    materials = pack.get("materials")
    if not materials and pack.get("material"):
        materials = [pack["material"]]
    if materials:
        payload["materials"] = materials if isinstance(materials, list) else [materials]

    # NOTE: price intentionally NOT in payload — owner sets price separately.
    # processing/shipping_profile/readiness are shop-level, not per-push.
    return {"payload": payload, "warnings": warnings}


def compile_catalog(sku: str) -> dict:
    """Pack → Etsy PATCH payload from pogpet/catalog/packs. (dirs 2, 7)

    Reads catalog listing block (title/tags/materials/description).
    Price resolved separately via release.resolve_price (never here).
    Description assembled by template.build_catalog_description.
    """
    import os as _os
    import sys as _sys
    _sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    try:
        from catalog import load as _cload, level as _level
    except ImportError:
        from pipeline.catalog import load as _cload, level as _level
    p = _cload(sku)
    listing = p.get("listing") or {}
    warnings: list[str] = []
    payload: dict = {}

    title = (listing.get("title") or "").strip()
    if len(title) > TITLE_MAX:
        warnings.append(f"title {len(title)} > {TITLE_MAX}, truncating")
        title = title[:TITLE_MAX].rsplit(" ", 1)[0]
    if title:
        payload["title"] = title

    # description via template (shape) + catalog fields (facts)
    try:
        from template import build_catalog_description
    except ImportError:
        from pipeline.compilers.template import build_catalog_description
    desc, dw = build_catalog_description(sku)
    payload["description"] = desc
    warnings += dw

    tags = normalize_tags(listing.get("tags") or [])
    if tags:
        payload["tags"] = tags

    # taxonomy: catalog packs don't carry Etsy taxonomy yet → gap, not guess
    # (caller resolves via taxonomy map or leaves for human)
    warnings.append("taxonomy: resolve from product type (not in catalog pack)")

    materials = listing.get("materials") or []
    if materials:
        payload["materials"] = materials

    return {"payload": payload, "warnings": warnings, "level": _level(sku)}


def diff_against_live(payload: dict, live: dict) -> dict:
    """Show what would change. Returns {field: (old, new)} for differing fields."""
    diff = {}
    for k, v in payload.items():
        old = live.get(k)
        if json_norm(old) != json_norm(v):
            diff[k] = {"old": old, "new": v}
    return diff


def json_norm(v):
    import json as _j
    return _j.dumps(v, sort_keys=True, default=str)
