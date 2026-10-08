"""Smart SVG logo generator — lettermarks + loading spinners per brand.

OddHobb uses its canonical emblem (figg brick-figure mark, static file).
Other brands get generated lettermarks in their palette until real marks
exist. Same generator powers tab icons, loading signs, and site favicons.
"""
from __future__ import annotations

PALETTES = {
    "oddhobb": {"bg1": "#AC64F6", "bg2": "#6425B9", "fg": "#FFFFFF",
                "accent": "#AC64F6", "initial": "O"},
    "pogtown": {"bg1": "#E8A33D", "bg2": "#9A5B0B", "fg": "#FFFFFF",
                "accent": "#E8A33D", "initial": "P"},
    "humanvoiced": {"bg1": "#22B8D4", "bg2": "#0B5B6B", "fg": "#FFFFFF",
                    "accent": "#22B8D4", "initial": "H"},
}
FALLBACK = {"bg1": "#569cd6", "bg2": "#2a5a8a", "fg": "#FFFFFF",
            "accent": "#569cd6", "initial": "?"}


def palette(slug: str) -> dict:
    return PALETTES.get((slug or "").lower(), FALLBACK)


def logo_svg(slug: str, size: int = 64) -> str:
    p = palette(slug)
    gid = f"g-{(slug or 'x').lower()}"
    wave = ""
    if (slug or "").lower() == "humanvoiced":
        wave = ('<path d="M14 44 q5 -12 10 0 t10 0 t10 0" fill="none" '
                'stroke="#FFFFFF" stroke-width="3" stroke-linecap="round" opacity=".85"/>')
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 64 64" role="img" aria-label="{slug} mark">'
        f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{p["bg1"]}"/>'
        f'<stop offset="1" stop-color="{p["bg2"]}"/></linearGradient></defs>'
        f'<rect width="64" height="64" rx="14" fill="url(#{gid})"/>'
        f'<text x="32" y="43" text-anchor="middle" font-family="system-ui,sans-serif" '
        f'font-size="30" font-weight="700" fill="{p["fg"]}">{p["initial"]}</text>{wave}</svg>'
    )


def spinner_svg(slug: str, size: int = 48, label: str = "") -> str:
    p = palette(slug)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 48 48" role="img" aria-label="loading {slug}">'
        f'<circle cx="24" cy="24" r="18" fill="none" stroke="{p["bg2"]}" '
        f'stroke-width="5" opacity=".25"/>'
        f'<circle cx="24" cy="24" r="18" fill="none" stroke="{p["accent"]}" '
        f'stroke-width="5" stroke-linecap="round" stroke-dasharray="28 85">'
        f'<animateTransform attributeName="transform" type="rotate" from="0 24 24" '
        f'to="360 24 24" dur="1s" repeatCount="indefinite"/></circle>'
        f'<text x="24" y="31" text-anchor="middle" font-family="system-ui,sans-serif" '
        f'font-size="16" font-weight="700" fill="{p["accent"]}">{p["initial"]}</text>'
        f'{f"<text x=24 y=46 text-anchor=middle font-size=8 fill=#808080>{label}</text>" if label else ""}</svg>'
    )
