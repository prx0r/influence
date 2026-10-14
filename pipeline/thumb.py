"""Thumbnail composer — art frame + title text → 1280x720 JPEG.

Sleep grammar: black field, single etched object, ≤3-word warm serif,
gold rule. No faces, no arrows. Pure PIL, $0, offline. Upload happens
via powvid thumbnails().set (50u, needs channel OAuth — separate step).
"""
from __future__ import annotations

import os

SIZE = (1280, 720)
MAX_BYTES = 2 * 1024 * 1024
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"


def _hex(h: str, default: tuple[int, int, int]) -> tuple[int, int, int]:
    try:
        h = h.strip().lstrip("#")
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    except Exception:
        return default


def compose(art_path: str, title_text: str, out_path: str,
            accent: str = "#D4A94E") -> dict:
    """Compose a thumbnail. Returns {out, size, bytes, under_2mb}."""
    from PIL import Image, ImageDraw, ImageFont, ImageEnhance
    if not os.path.isfile(art_path):
        return {"ok": False, "reason": f"no art: {art_path}"}
    words = [w for w in (title_text or "").split() if w]
    if len(words) > 3:
        return {"ok": False,
                "reason": f"{len(words)} words: 3-word max for sleep thumbs"}
    bg = Image.open(art_path).convert("RGB")
    # cover-crop to 16:9
    tr, br = SIZE[0] / SIZE[1], bg.size[0] / bg.size[1]
    if br > tr:
        w = int(bg.size[1] * tr)
        x = (bg.size[0] - w) // 2
        bg = bg.crop((x, 0, x + w, bg.size[1]))
    else:
        h = int(bg.size[0] / tr)
        y = (bg.size[1] - h) // 2
        bg = bg.crop((0, y, bg.size[0], y + h))
    bg = bg.resize(SIZE, Image.LANCZOS)
    bg = ImageEnhance.Brightness(bg).enhance(0.55)  # darken for text
    d = ImageDraw.Draw(bg)
    gold = _hex(accent, (212, 169, 78))
    # gold rule above title zone
    d.rectangle([80, SIZE[1] - 220, 240, SIZE[1] - 214], fill=gold)
    try:
        font = ImageFont.truetype(FONT, 92)
    except Exception:
        font = ImageFont.load_default()
    y = SIZE[1] - 200
    for line in [" ".join(words)]:
        d.text((80, y), line, font=font, fill=(245, 240, 230))
        y += 110
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    bg.save(out_path, "JPEG", quality=88)
    n = os.path.getsize(out_path)
    return {"ok": True, "out": out_path, "size": SIZE, "bytes": n,
            "under_2mb": n <= MAX_BYTES, "title": " ".join(words)}
