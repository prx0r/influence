"""Amazon compiler — pack → Amazon listing copy + flat-file row.

Amazon Handmade/standard: title ≤200 chars (no promo phrases),
5 bullets ≤500 chars each, description (HTML ok), backend search terms
(≤250 bytes total), no taxonomy_id (browse nodes assigned in Seller Central).
Outputs copy + TSV row for flat-file upload. No API push (manual upload).
"""
from __future__ import annotations

TITLE_MAX = 200
BULLET_MAX = 500
BULLETS_N = 5
SEARCH_TERMS_BYTES = 250

BANNED_PHRASES = ("best seller", "number 1", "#1", "free shipping",
                  "guaranteed", "!!!", "%%")


def _clean_title(title: str) -> tuple[str, list[str]]:
    warnings: list[str] = []
    t = " ".join((title or "").split())
    for phrase in BANNED_PHRASES:
        if phrase.lower() in t.lower():
            warnings.append(f"removed banned phrase: {phrase!r}")
            t = t.replace(phrase, "").replace(phrase.title(), "")
    t = " ".join(t.split())
    if len(t) > TITLE_MAX:
        warnings.append(f"title {len(t)} > {TITLE_MAX}, truncating")
        t = t[:TITLE_MAX].rsplit(" ", 1)[0]
    return t, warnings


def _bullets(pack: dict, desc: str) -> list[str]:
    """5 bullets from pack: what/maat/personalisation/shipping/gift."""
    desc_lines = [l.strip("•- ").strip() for l in desc.split("\n") if l.strip()]
    material = pack.get("material") or pack.get("material_primary") or "quality materials"
    size = ""
    ref_geo = pack.get("reference_geometry") or ""
    bullets = [
        f"Personalised {pack.get('sku', 'gift').replace('-', ' ').replace('_', ' ').title()} — made to order from your photo or message.",
        f"Material: {material}. {ref_geo}"[:BULLET_MAX].strip(),
        "How it works: order → upload photo/message → approve preview → we make and ship.",
        "Gift-ready packaging. Makes a thoughtful stocking filler or keepsake gift.",
        "Made to order — please allow processing time shown. Message us for rush options.",
    ]
    # prefer real description lines where they fit
    for i, line in enumerate(desc_lines[:BULLETS_N]):
        if line and len(line) <= BULLET_MAX and len(line) > 20:
            bullets[i] = line[:BULLET_MAX]
    return [b[:BULLET_MAX] for b in bullets[:BULLETS_N]]


def _search_terms(pack: dict) -> str:
    """Backend terms ≤250 bytes, no duplicates, no brand spam."""
    seen: set[str] = set()
    out: list[str] = []
    for t in (pack.get("tags") or [])[:13]:
        t = str(t).strip().lower()
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    joined = " ".join(out)
    while len(joined.encode()) > SEARCH_TERMS_BYTES and out:
        out.pop()
        joined = " ".join(out)
    return joined


def compile_amazon(pack: dict) -> dict:
    warnings: list[str] = []
    title, w = _clean_title(pack.get("etsy_title") or pack.get("sku", ""))
    warnings += w
    desc = (pack.get("description") or "").strip()
    bullets = _bullets(pack, desc)
    terms = _search_terms(pack)
    price = pack.get("price")
    sku = pack.get("sku", "")
    row = {
        "sku": sku,
        "product-id-type": "1",  # placeholder: assign GTIN/UPC exemption in Seller Central
        "item-name": title,
        "bullet-point-1": bullets[0] if len(bullets) > 0 else "",
        "bullet-point-2": bullets[1] if len(bullets) > 1 else "",
        "bullet-point-3": bullets[2] if len(bullets) > 2 else "",
        "bullet-point-4": bullets[3] if len(bullets) > 3 else "",
        "bullet-point-5": bullets[4] if len(bullets) > 4 else "",
        "product-description": desc[:2000],
        "generic-keywords": terms,
        "standard-price": price or "",
        "quantity": "100",
        "main-image-url": (pack.get("assets_now") or [""])[0] if pack.get("assets_now") else "",
    }
    if not price:
        warnings.append("no price — fill standard-price before upload")
    if not row["main-image-url"]:
        warnings.append("no hero image — Amazon requires images before publish")
    return {"title": title, "bullets": bullets, "search_terms": terms,
            "description": desc[:2000], "tsv_row": row, "warnings": warnings}


def tsv_header() -> list[str]:
    return ["sku", "product-id-type", "item-name", "bullet-point-1",
            "bullet-point-2", "bullet-point-3", "bullet-point-4",
            "bullet-point-5", "product-description", "generic-keywords",
            "standard-price", "quantity", "main-image-url"]
