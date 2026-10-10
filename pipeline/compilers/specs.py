"""Spec compiler — catalog pack → exact specs for image prompts + listings.

Reads ONLY from pogpet/catalog/packs (canonical product truth).
Generic scale references (coin = 24.5mm) may remain — those are rendering
helpers, not product facts. Product dims NEVER live here.

Missing truth → gap (drives a pack-repair task). Never guess.
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
try:
    from catalog import physical_truth, REFERENCES
except ImportError:
    from pipeline.catalog import physical_truth, REFERENCES  # noqa

# Re-export generic references for prompt grounding (rendering helpers only)
__all__ = ["compile_specs", "REFERENCES"]


def compile_specs(sku: str) -> dict:
    """Catalog pack → {spec_block, scale_prompt, gaps}.

    spec_block: human-readable specs for listings/infographics.
    scale_prompt: exact sentence for image prompts grounding true size.
    gaps: missing truth → pack-repair tasks, never guesses.
    """
    gaps: list[str] = []
    try:
        t = physical_truth(sku)
    except (OSError, ValueError, KeyError):
        return {"spec_block": "", "scale_prompt": "",
                "gaps": [f"{sku}: no catalog pack (cannot compile specs)"],
                "material": "", "size_class": "", "dims": "",
                "weight": "", "verified": False, "source": "missing"}

    dims = t.get("dims_mm") or []
    material = t.get("material") or ""
    if not dims:
        gaps.append(f"{sku}: no dims_mm in catalog pack (measure product / repair pack)")
    if not material:
        gaps.append(f"{sku}: no material in catalog pack")

    dims_str = " × ".join(str(d) for d in dims) + " mm" if dims else "?"
    spec_block = f"Material: {material or '?'}."
    if dims:
        spec_block += f" Size: {dims_str}."
    lead_b = t.get("lead_build_days")
    lead_min, lead_max = t.get("lead_ship_min"), t.get("lead_ship_max")
    if lead_b:
        spec_block += f" Made to order (~{lead_b} working days production)."
    if lead_min and lead_max:
        spec_block += f" Delivery {lead_min}-{lead_max} working days."

    # scale grounding: pick reference near product size
    max_dim = max(dims) if dims else 0
    if max_dim <= 30:
        ref_key, ref_how = "gb_10p", "next to a UK 10p coin (24.5mm)"
    elif max_dim <= 90:
        ref_key, ref_how = "credit_card", "next to a credit card (85.6mm)"
    elif max_dim <= 220:
        ref_key, ref_how = "mug", "next to a standard mug (95mm tall)"
    else:
        ref_key, ref_how = "paperback", "next to a paperback book (198mm)"
    ref = REFERENCES.get(ref_key, {})
    scale_prompt = ""
    if dims:
        scale_prompt = (
            f"The product measures exactly {dims_str}. "
            f"For scale it appears {ref_how} at true relative size."
        )

    return {"spec_block": spec_block, "scale_prompt": scale_prompt,
            "gaps": gaps, "material": material,
            "size_class": "", "dims": dims_str,
            "weight": "", "verified": True,
            "source": f"catalog:{sku}",
            "pack_hash": t.get("pack_hash", "")[:16],
            "supplier": t.get("supplier", ""),
            "lead_build_days": lead_b,
            "lead_ship": [lead_min, lead_max]}


# Generic scale references live in catalog.py REFERENCES (rendering helpers).
# Product dims NEVER live here (dir 3).


if __name__ == "__main__":
    import argparse
    import json as _j
    ap = argparse.ArgumentParser()
    ap.add_argument("sku", nargs="?", default=None)
    args = ap.parse_args()
    if args.sku:
        print(_j.dumps(compile_specs(args.sku), indent=1))
