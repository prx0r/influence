"""Brand context loader — bgraph is the spine, pipeline reads it.

Reads /root/bgraph/registry/brands/<slug>.json → style, voice, handles,
etsy structures (when present). Compilers call get_context(slug) for
brand-aware copy. Missing/empty fields return defaults + gaps (never crash).

bgraph is READ-ONLY from here. Style fills happen in bgraph repo with owner approval.
"""
from __future__ import annotations

import json
import os

BGRAPH = os.getenv("BGRAPH_ROOT", "/root/bgraph/registry/brands")

DEFAULT_VOICE = "Warm, specific, anti-generic."
DEFAULT_STYLE = {"background": "warm cream #F7F3EE", "lighting": "soft key, warm fill", "avoid": []}


def brand_file(slug: str) -> str:
    return os.path.join(BGRAPH, f"{slug}.json")


def load_brand(slug: str) -> dict:
    with open(brand_file(slug)) as f:
        return json.load(f)


def get_context(slug: str = "oddhobb") -> dict:
    """Full brand context for compilers. Always returns usable defaults."""
    try:
        d = load_brand(slug)
    except (OSError, ValueError):
        return {"slug": slug, "missing": True, "voice": DEFAULT_VOICE,
                "style": dict(DEFAULT_STYLE), "handles": {}, "etsy": {},
                "gaps": [f"no bgraph file for {slug}"]}
    ident = d.get("identity", {})
    gaps = []
    voice = ident.get("voice") or ""
    if not voice:
        gaps.append(f"{slug}: no voice in bgraph")
        voice = DEFAULT_VOICE
    style = ident.get("style_lock") or {}
    # treat TODO stubs as missing
    clean_style = {k: v for k, v in style.items()
                   if v not in ("TODO", "", [], {}) or k == "avoid"}
    if not clean_style.get("background"):
        gaps.append(f"{slug}: style_lock.background is TODO")
    handles = {}
    for b in d.get("branches", []):
        plat = b.get("platform", "")
        acct = (b.get("account") or {})
        if plat and acct.get("handle"):
            handles[plat] = {"handle": acct["handle"], "status": acct.get("status", "")}
    etsy = d.get("etsy") or ident.get("etsy") or {}
    if not etsy:
        gaps.append(f"{slug}: no etsy structures in bgraph")
    return {"slug": slug, "display_name": ident.get("display_name", slug),
            "domain": ident.get("domain", ""), "voice": voice,
            "style": {**DEFAULT_STYLE, **clean_style},
            "handles": handles, "etsy": etsy, "gaps": gaps,
            "design_thesis": ident.get("design_thesis", "")}


def voice_for(slug: str = "oddhobb") -> str:
    return get_context(slug)["voice"]


def style_for(slug: str = "oddhobb") -> dict:
    return get_context(slug)["style"]


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", nargs="?", default="oddhobb")
    args = ap.parse_args()
    print(json.dumps(get_context(args.slug), indent=1)[:2000])
