"""Social compiler — pack → X/IG/TikTok/YouTube variants.

Channel-native: X has no URL in body ($0.015 vs $0.20), IG needs hashtags,
TikTok needs hook-first script, YT needs title+description. All drafts —
human_confirm before anything publishes.
"""
from __future__ import annotations

X_MAX = 280


def _base(pack: dict) -> dict:
    title = (pack.get("etsy_title") or pack.get("sku", "")).split("|")[0].strip()
    price = pack.get("price")
    tags = (pack.get("tags") or [])[:5]
    desc = (pack.get("description") or "").strip().split("\n")[0][:200]
    image = ""
    if pack.get("assets_now"):
        image = pack["assets_now"][0]
    elif pack.get("etsy_image_url"):
        image = pack["etsy_image_url"]
    return {"title": title, "price": price, "tags": tags,
            "desc": desc, "image": image, "sku": pack.get("sku", "")}


def compile_x(pack: dict, shop_url: str = "") -> dict:
    """X post: hook + product + price. NO URL in body (put in bio/reply)."""
    b = _base(pack)
    price_bit = f" ${b['price']}" if b["price"] else ""
    text = f"{b['title']}{price_bit}. {b['desc']}"
    text = " ".join(text.split())
    if len(text) > X_MAX:
        text = text[:X_MAX].rsplit(" ", 1)[0] + "…"
    return {"text": text, "image_url": b["image"] or None,
            "reply_with_link": shop_url or None,  # link goes in reply, not body
            "cost_note": "no URL in body = $0.015 (URL body = $0.20)"}


def compile_instagram(pack: dict, brand_tags: list[str] | None = None) -> dict:
    b = _base(pack)
    hashtags = ["#" + "".join(t.split())[:20] for t in b["tags"][:8]]
    hashtags += brand_tags or ["#oddhobb", "#personalisedgift"]
    caption = (f"{b['title']}\n\n{b['desc']}\n\n"
               f"Link in bio.\n\n" + " ".join(hashtags[:15]))
    return {"caption": caption[:2200], "image_url": b["image"] or None,
            "hashtags": hashtags[:15]}


def compile_tiktok(pack: dict) -> dict:
    """Script outline: hook (0-3s) → reveal (3-8s) → CTA. Video from renders."""
    b = _base(pack)
    return {
        "hook_0_3s": f"POV: your {b['title'].lower()} arrives",
        "reveal_3_8s": b["desc"],
        "cta": "Link in bio — made to order",
        "caption": f"{b['title']} {' '.join('#'+''.join(t.split())[:20] for t in b['tags'][:5])}"[:150],
        "image_url": b["image"] or None,
    }


def compile_youtube(pack: dict) -> dict:
    b = _base(pack)
    return {
        "title": f"{b['title']} — Personalised Gift"[:100],
        "description": f"{b['desc']}\n\nMade to order. Link below."[:1000],
        "tags": [t[:30] for t in b["tags"][:10]],
        "image_url": b["image"] or None,  # thumbnail source
    }


def compile_all(pack: dict, shop_url: str = "",
                brand_tags: list[str] | None = None) -> dict:
    return {
        "x": compile_x(pack, shop_url),
        "instagram": compile_instagram(pack, brand_tags),
        "tiktok": compile_tiktok(pack),
        "youtube": compile_youtube(pack),
    }
