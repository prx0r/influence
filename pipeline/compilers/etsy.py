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
