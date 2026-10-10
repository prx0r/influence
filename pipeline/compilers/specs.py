"""Spec compiler — pack → exact specs for image prompts + listings.

Pulls material/dims/weight from pack fields. Falls back to size-class
defaults. Flags missing dims as pack gaps (drives sample-and-measure).
Scale references are real-world objects with known mm for prompt grounding.
"""
from __future__ import annotations

# Real-world scale references with true dimensions (mm)
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

# Size-class defaults (mm) when pack has no exact dims — flagged as estimates
SIZE_CLASS_DEFAULTS = {
    "tiny": {"dims_mm": "15-30", "example": "croc charm 28mm", "ref": "gb_10p"},
    "small": {"dims_mm": "50-80", "example": "keychain 60-80mm", "ref": "credit_card"},
    "mid": {"dims_mm": "100-200", "example": "desk objects", "ref": "mug"},
    "large": {"dims_mm": "200+", "example": "boards, racks", "ref": "paperback"},
    "sheet": {"dims_mm": "flat sheet", "example": "wrap, cards", "ref": "a4"},
}

# Verified dims (measured or from production docs). Beatt size_class when present.
# Source noted per entry. Add rows as samples get measured.
KNOWN_DIMS = {
    "CHARM-CROC-JIBBIT": {"dims": "28mm diameter", "weight": "3-8g",
                           "ref": "croc_hole", "source": "pogpet docs/balance.md"},
    "CHARM-BAG": {"dims": "28mm", "weight": "", "ref": "gb_10p", "source": "same family as croc"},
    "CHARM-SHOELACE": {"dims": "28mm", "weight": "", "ref": "gb_10p", "source": "same family as croc"},
    "KEYCHAIN-PET": {"dims": "60-80mm", "weight": "30-80g",
                     "ref": "credit_card", "source": "pogpet docs/balance.md"},
    "KEYCHAIN-BRICK": {"dims": "60-80mm", "weight": "", "ref": "credit_card", "source": "pogpet docs/balance.md"},
    "KEYCHAIN-COUPLE-BRICK": {"dims": "60-80mm", "weight": "", "ref": "credit_card", "source": "pogpet docs/balance.md"},
    "BRICK-FIGURE": {"dims": "8cm tall", "weight": "25-35g",
                     "ref": "fingertip", "source": "Etsy 4584650499 copy + how-to image"},
    "ORNAMENT": {"dims": "80mm", "weight": "50-120g",
                 "ref": "mug", "source": "pogpet docs/balance.md"},
    "POSTCARD-SET-CUSTOM": {"dims": "A6 105x148mm", "weight": "",
                            "ref": "a4", "source": "Prodigi CLASSIC-POST-GLOS-6X4 class"},
    "GOLF-MARKER": {"dims": "24mm disc", "weight": "",
                    "ref": "gb_1", "source": "pogpet golf marker spec"},
}


def compile_specs(pack: dict) -> dict:
    """Pack → {spec_block, scale_prompt, gaps}.

    spec_block: human-readable specs for listings/infographics.
    scale_prompt: exact sentence for image prompts grounding true size.
    gaps: missing dims that need sample-and-measure.
    """
    gaps: list[str] = []
    sku = pack.get("sku", "?")
    material = pack.get("material") or pack.get("material_primary") or ""
    size_class = pack.get("size_class") or ""
    verified = False

    # 1. pack fields, 2. known dims table, 3. size-class estimate
    dims = pack.get("dims_mm") or pack.get("dimensions_mm") or ""
    weight = pack.get("weight_g") or pack.get("weight") or ""
    source = "pack"
    if not dims and sku in KNOWN_DIMS:
        dims = KNOWN_DIMS[sku]["dims"]
        source = "known (" + KNOWN_DIMS[sku]["source"] + ")"
        verified = True
    if not weight and sku in KNOWN_DIMS and KNOWN_DIMS[sku].get("weight"):
        weight = KNOWN_DIMS[sku]["weight"]
    if not dims:
        gaps.append(f"{sku}: no exact dims in pack (need sample-and-measure)")
        default = SIZE_CLASS_DEFAULTS.get(size_class, {})
        dims = default.get("dims_mm", "?") + " (est.)" if default else "?"
    if not weight:
        gaps.append(f"{sku}: no weight in pack")

    spec_block = f"Material: {material or '?'}."
    if dims and dims != "?":
        spec_block += f" Size: {dims}."
    if weight:
        spec_block += f" Weight: {weight}."

    # scale grounding for prompts (known ref wins over size-class)
    ref_key = ""
    if sku in KNOWN_DIMS and KNOWN_DIMS[sku].get("ref"):
        ref_key = KNOWN_DIMS[sku]["ref"]
    else:
        ref_key = (SIZE_CLASS_DEFAULTS.get(size_class, {}) or {}).get("ref", "")
    ref = REFERENCES.get(ref_key, {})
    scale_prompt = ""
    if ref and dims and not dims.endswith("(est.)"):
        scale_prompt = (
            f"The product is exactly {dims}. "
            f"For scale, a {ref['label']} ({ref.get('dia_mm') or ref.get('height_mm')}mm) "
            f"appears alongside it at true relative size."
        )
    elif ref:
        scale_prompt = (
            f"The product is approximately {dims}. "
            f"Show it next to a {ref['label']} for honest scale."
        )

    return {"spec_block": spec_block, "scale_prompt": scale_prompt,
            "gaps": gaps, "material": material,
            "size_class": size_class, "dims": dims, "weight": weight or "",
            "verified": verified, "source": source}


if __name__ == "__main__":
    import argparse, json, sys, os as _os
    sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    try:
        from compilers.pack_loader import load
    except ImportError:
        from pipeline.compilers.pack_loader import load
    ap = argparse.ArgumentParser()
    ap.add_argument("sku", nargs="?", default=None)
    ap.add_argument("--store", default="oddhobb")
    ap.add_argument("--all", action="store_true", help="gap report across all packs")
    args = ap.parse_args()
    if args.all:
        try:
            from compilers.pack_loader import list_packs
        except ImportError:
            from pipeline.compilers.pack_loader import list_packs
        all_gaps = []
        for p in list_packs(args.store):
            full = load(args.store, p["sku"])
            r = compile_specs(full)
            all_gaps.extend(r["gaps"])
        print(f"{len(all_gaps)} spec gaps:")
        for g in all_gaps:
            print(" ", g)
    elif args.sku:
        print(json.dumps(compile_specs(load(args.store, args.sku)), indent=1))
