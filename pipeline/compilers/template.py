"""Listing templates — the coherent-feel engine.

Every OddHobb listing follows the same shape so the store feels like one brand:
- Description sections in fixed order (hook → what → how → specs → shipping → sign-off)
- Image slots with roles (hero required, rest aspirational)
- Brand rules enforced (sign-off line, no price in copy, honest processing)

Packs supply the content. Templates supply the shape. Compilers merge them.
"""
from __future__ import annotations

# ── description sections (fixed order) ──────────────────────────────────
SECTIONS = ("hook", "what", "how", "specs", "shipping", "brand")

BRAND_SIGNOFF = "— OddHobb · odd little gifts for the things they're obsessed with."


def brand_signoff(brand_slug: str = "oddhobb") -> str:
    """Sign-off from bgraph voice. Falls back to OddHobb default."""
    try:
        import os as _os
        import sys as _sys
        _sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
        try:
            from brand import get_context
        except ImportError:
            from pipeline.brand import get_context
        ctx = get_context(brand_slug)
        disp = ctx.get("display_name", brand_slug)
        dom = ctx.get("domain", "")
        if disp and dom:
            return f"— {disp} · {dom}"
    except Exception:
        pass
    return BRAND_SIGNOFF

# ── image slots ─────────────────────────────────────────────────────────
# Full spec: oddhobbies/etsy-pack/IMAGES.md (deconstructed from listing
# 4584650499 "Your Own Brick Figure"). 5 essential images, fixed order.
# Slots 6-10 reserved for future expansion; Etsy allows 10.
IMAGE_SLOTS = [
    {"slot": 1, "role": "hero", "required": True,
     "desc": "Main product image — clean surface, warm light, fills frame"},
    {"slot": 2, "role": "in_use", "required": False,
     "desc": "In-use / lifestyle — product in context"},
    {"slot": 3, "role": "scale", "required": False,
     "desc": "Scale reference — next to everyday object"},
    {"slot": 4, "role": "variants", "required": False,
     "desc": "All variants — coats, hats, sizes, colours"},
    {"slot": 5, "role": "detail", "required": False,
     "desc": "Detail close-up — loop, texture, print quality"},
    {"slot": 6, "role": "packaging", "required": False,
     "desc": "Packaging — gift-ready presentation"},
    {"slot": 7, "role": "size_diagram", "required": False,
     "desc": "Size diagram with measurements"},
    {"slot": 8, "role": "personalisation", "required": False,
     "desc": "Personalisation example — name / message shown"},
    {"slot": 9, "role": "bundle", "required": False,
     "desc": "Bundle shot — with complementary products"},
    {"slot": 10, "role": "mesh", "required": False,
     "desc": "Mesh / 3D viewer still — the digital original"},
]


def build_description(pack: dict, specs_block: str = "",
                      shipping_block: str = "") -> tuple[str, list[str]]:
    """Assemble description from pack + template sections. Returns (text, warnings)."""
    warnings: list[str] = []
    parts: list[str] = []

    # HOOK — first line of pack description, or title
    desc = (pack.get("description") or "").strip()
    if desc:
        first = desc.split("\n")[0].strip()
        parts.append(first)
        rest = "\n".join(desc.split("\n")[1:]).strip()
    else:
        title = (pack.get("etsy_title") or pack.get("sku", "")).split("|")[0].strip()
        parts.append(title)
        rest = ""
        warnings.append("no description in pack — hook fell back to title")

    # WHAT YOU GET — rest of pack description
    if rest:
        parts.append("WHAT YOU GET\n" + rest)

    # HOW TO ORDER — shape only. Steps are generic process (place → send →
    # approve → made), never operational promises. Preview timing, rush
    # options, and delivery promises come from the pack or not at all.
    # (dir 6: templates define shape, never invent facts.)
    parts.append(
        "HOW TO ORDER\n"
        "1. Place your order.\n"
        "2. Send your photo / name / message (Etsy message or email).\n"
        "3. You approve the preview — we make and ship."
    )

    # SPECS — caller-supplied block (from catalog specs compiler) or nothing.
    # Never invent material/dims here.
    if specs_block:
        parts.append(specs_block)
    else:
        warnings.append("no specs block — pass catalog spec_block (never guess)")

    # SHIPPING — caller-supplied delivery windows from catalog lead times,
    # or nothing. Never invent promises.
    if shipping_block:
        parts.append(shipping_block)
    else:
        warnings.append("no shipping block — pass catalog lead times (never promise)")

    # BRAND — always last, always identical
    parts.append(BRAND_SIGNOFF)

    text = "\n\n".join(parts)
    # coherence: no price in copy (price lives in price field)
    price = pack.get("price")
    if price and str(price) in text:
        warnings.append("price appears in description copy — remove (lives in price field)")
    return text, warnings


def build_catalog_description(sku: str) -> tuple[str, list[str]]:
    """Description from catalog pack truth. (dirs 2, 6)

    Shape from template sections. EVERY factual sentence compiles from the
    pack: description, spec_rows, processing. Nothing invented. No "24 hours",
    no "rush options", no promises the pack doesn't make.
    """
    import os as _os
    import sys as _sys
    _sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    try:
        from catalog import load as _cload
    except ImportError:
        from pipeline.catalog import load as _cload
    warnings: list[str] = []
    p = _cload(sku)
    listing = p.get("listing") or {}
    parts: list[str] = []

    desc = (listing.get("description") or "").strip()
    short = (listing.get("short") or "").strip()
    if short:
        parts.append(short)
    elif desc:
        parts.append(desc.split("\n")[0].strip())
    else:
        parts.append(p.get("name", sku))
        warnings.append("no description/short in catalog pack")

    if desc and short and desc != short:
        parts.append("WHAT YOU GET\n" + desc)

    # HOW TO ORDER — shape only, no timing promises (dir 6)
    parts.append(
        "HOW TO ORDER\n"
        "1. Place your order.\n"
        "2. Send your photo / name / message (Etsy message or email).\n"
        "3. You approve the preview — we make and ship."
    )

    # SPECS — spec_rows verbatim from catalog (dir 2: pack truth)
    rows = listing.get("spec_rows") or []
    if rows:
        parts.append("SPECS\n" + "\n".join(
            f"{r[0]}: {r[1]}" for r in rows if len(r) == 2))
    else:
        warnings.append("no spec_rows in catalog pack")

    # SHIPPING — processing verbatim from catalog, nothing added
    proc = (listing.get("processing") or "").strip()
    if proc:
        parts.append("SHIPPING\n" + proc)
    else:
        warnings.append("no processing in catalog pack (no promises made)")

    parts.append(BRAND_SIGNOFF)
    return "\n\n".join(parts), warnings


def image_checklist(pack: dict) -> dict:
    """Map pack assets to the 10 slots. Returns {slots, missing_required, score}."""
    assets = pack.get("assets_now") or []
    etsy_url = pack.get("etsy_image_url") or ""
    slots = []
    for spec in IMAGE_SLOTS:
        has = False
        src = ""
        if spec["slot"] == 1 and (assets or etsy_url):
            has, src = True, (assets[0] if assets else etsy_url)
        slots.append({"slot": spec["slot"], "role": spec["role"],
                      "required": spec["required"], "desc": spec["desc"],
                      "has": has, "src": src})
    missing_required = [s["role"] for s in slots if s["required"] and not s["has"]]
    have = sum(1 for s in slots if s["has"])
    return {"slots": slots, "missing_required": missing_required,
            "score": f"{have}/10", "hero_ok": not missing_required}


def coherence_check(pack: dict, description: str) -> list[str]:
    """Brand rules. Returns violations (empty = coherent)."""
    issues = []
    if not description.rstrip().endswith(BRAND_SIGNOFF.rstrip(".")):
        # allow trailing period variance
        if BRAND_SIGNOFF.split("—")[1].strip()[:20] not in description:
            issues.append("missing brand sign-off")
    price = pack.get("price")
    if price and f"${price}" in description:
        issues.append("price in copy (belongs in price field)")
    if len(description) < 200:
        issues.append(f"description too short ({len(description)} chars)")
    tags = pack.get("tags") or []
    if len(tags) < 10:
        issues.append(f"only {len(tags)} tags (aim 13)")
    return issues
