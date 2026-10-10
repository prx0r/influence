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

# ── image slots (Etsy allows 10) ────────────────────────────────────────
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

    # HOW TO ORDER — standard flow (personalised products)
    parts.append(
        "HOW TO ORDER\n"
        "1. Place your order.\n"
        "2. Send your photo / name / message (Etsy message or email).\n"
        "3. We create a preview within 24 hours.\n"
        "4. You approve — we make and ship."
    )

    # SPECS — caller-supplied (Prodigi dims, materials) or pack material
    if specs_block:
        parts.append(specs_block)
    elif pack.get("material"):
        parts.append(f"SPECS\nMaterial: {pack['material']}.")

    # SHIPPING — caller-supplied delivery windows, or generic honest fallback
    if shipping_block:
        parts.append(shipping_block)
    else:
        parts.append(
            "SHIPPING\nMade to order. Processing time shown above. "
            "Message us for rush options."
        )
        warnings.append("generic shipping block — pass real delivery windows")

    # BRAND — always last, always identical
    parts.append(BRAND_SIGNOFF)

    text = "\n\n".join(parts)
    # coherence: no price in copy (price lives in price field)
    price = pack.get("price")
    if price and str(price) in text:
        warnings.append("price appears in description copy — remove (lives in price field)")
    return text, warnings


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
