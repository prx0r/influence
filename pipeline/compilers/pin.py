"""Pinterest pin compiler — pack → pin payload.

Rides the Shopify sales channel today; native Pins API when token lands.
Board maps from pack shop_section_target. Title = SEO title, description
= hook + CTA. Image = best asset (suitability.pinterest in asset labels).
"""
from __future__ import annotations

BOARD_MAP = {
    "Featured": "OddHobb Gifts",
    "Couples & Weddings": "Couples Gifts",
    "Game Night": "Game Night Gifts",
    "Physical Media": "Memory Gifts",
    "Add-Ons": "Stocking Fillers",
}


def compile_pin(pack: dict, shop_url: str = "") -> dict:
    title = (pack.get("etsy_title") or pack.get("sku", "")).split("|")[0].strip()
    desc_lines = [l.strip("•- ").strip() for l in (pack.get("description") or "").split("\n") if l.strip()]
    hook = desc_lines[0][:300] if desc_lines else title
    price = pack.get("price")
    price_bit = f" ${price}" if price else ""
    description = f"{hook}{price_bit}. Made to order — link to shop."
    if len(description) > 500:
        description = description[:500].rsplit(" ", 1)[0]
    section = pack.get("shop_section_target") or pack.get("section") or "Featured"
    board = BOARD_MAP.get(section, "OddHobb Gifts")
    image = ""
    if pack.get("assets_now"):
        image = pack["assets_now"][0]
    elif pack.get("etsy_image_url"):
        image = pack["etsy_image_url"]
    warnings = []
    if not image:
        warnings.append("no image — pin needs an image before publish")
    return {
        "title": title[:100],
        "description": description,
        "board": board,
        "link": shop_url or None,
        "image_url": image or None,
        "alt_text": title[:200],
        "warnings": warnings,
    }
