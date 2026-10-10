"""Price table — every action has a known price before it runs.

Free actions (Etsy PATCH, Prodigi quote) still get action rows at $0.00.
Paid actions need a grant before they execute. See RUNTIME.md.
"""
from __future__ import annotations

# USD per single call unless noted
COSTS_USD: dict[str, float] = {
    # fal.ai (hosted)
    "fal.flux_schnell": 0.01,
    "fal.flux_dev": 0.025,
    "fal.flux_pro_edit": 0.05,
    "fal.recraft": 0.04,
    "fal.recraft_style": 0.005,      # one-time style_id creation
    "fal.flux_lora_train": 2.00,
    "fal.birefnet": 0.01,
    "fal.kling_video": 0.25,         # per 5s
    "fal.upscale": 0.01,
    # Alibaba direct (Singapore pricing)
    "qwen.image_3_std": 0.033,       # $0.003 input + $0.03 output
    "qwen.image_3_pro": 0.043,
    "qwen.wan_27": 0.03,
    "qwen.wan_27_pro": 0.075,
    "qwen.chat_turbo": 0.0001,       # est per call
    "qwen.chat_plus": 0.001,
    "qwen.chat_flash": 0.0005,
    # Higgsfield
    "higgsfield.soul_id": 2.50,      # one-time identity
    "higgsfield.soul_2": 0.005,      # per image
    "higgsfield.product_shot": 0.05,  # est
    "higgsfield.marketing": 0.05,    # est
    # Social (per post)
    "x.post_plain": 0.015,           # no URL
    "x.post_url": 0.20,              # with URL — 13x!
    # Meshy (verified docs.meshy.ai 2026-10-10, credits — $ value varies by plan)
    "meshy.text3d_preview": 20,      # credits, mesh only
    "meshy.text3d_textured": 30,     # credits, mesh + 2K texture
    "meshy.refine_2k": 10,           # credits, texture only
    "meshy.rig": 5,                  # credits per request
    "meshy.anim": 3,                 # credits per action (up to 10)
    # sleepdraw (verified COSTS.md 2026-09-27)
    "sleepdraw.art_cf_flux": 0.0,     # CF Workers AI free allocation
    "sleepdraw.draw_cpu": 0.0,        # local CPU
    "sleepdraw.ship_r2": 0.0,         # $0.015/GB-mo, negligible
    "sleepdraw.edit_fal": 0.024,      # fal flux-2/edit per img
    "sleepdraw.breathe_fal": 0.075,   # fal i2v midpoint $0.05-0.10
    "sleepdraw.bed_fal": 0.035,       # fal ACE-Step midpoint
    "sleepdraw.film_10min": 0.70,     # all-in 10-min film
    # Free (still logged)
    "etsy.listing_update": 0.0,
    "etsy.listing_read": 0.0,
    "prodigi.quote": 0.0,
    "prodigi.product_read": 0.0,
    "shopify.product_read": 0.0,
    "shopify.product_push": 0.0,
    "mixam.quote": 0.0,
    "printify.catalog_read": 0.0,
}

# Thresholds for notification urgency
SPEND_SMS_THRESHOLD_USD = 1.00   # SMS on any single action > $1
SPEND_TASK_HIGH_USD = 5.00       # high-urgency task above this


def price_for(capability: str) -> float:
    """USD cost for one call. Unknown capabilities return None (must not guess)."""
    return COSTS_USD.get(capability)


def to_cents(usd: float) -> int:
    return int(round(usd * 100))
