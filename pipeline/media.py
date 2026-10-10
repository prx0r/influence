"""Media assembly — lightweight, no Blender, no Docker, no model downloads.

PIL composite (background + product foreground) + ffmpeg slideshow/zoompan.
Backgrounds: generated once via fal/Qwen (when keys land) or flat colour.
Foreground: real product renders/photos from the pack (never AI-invented).

Every output carries a manifest: inputs, template, mesh version, cost.
"""
from __future__ import annotations

import json
import os
import subprocess

# Etsy media limits (Oct 2026)
PHOTO_MIN_PX = 2000       # recommended
PHOTO_FIRST_MIN_PX = 635  # minimum for first image
VIDEO_MIN_S = 5
VIDEO_MAX_S = 15
VIDEO_MAX_MB = 100
VIDEO_TARGET_MB = 20
VIDEO_RES = (1080, 1080)  # square works everywhere; 1080x1920 for vertical


def _pil():
    try:
        from PIL import Image
        return Image
    except ImportError:
        raise RuntimeError("PIL required: pip install pillow")


def composite(foreground_path: str, background_path: str | None,
              out_path: str, size: tuple[int, int] = (2000, 2000),
              bg_color: tuple[int, int, int] = (247, 243, 238)) -> dict:
    """Product foreground onto background (or flat OddHobb cream). Returns manifest."""
    Image = _pil()
    fg = Image.open(foreground_path).convert("RGBA")
    # fit foreground to 80% of canvas, keep aspect
    fw, fh = fg.size
    scale = min(size[0] * 0.8 / fw, size[1] * 0.8 / fh)
    fg = fg.resize((int(fw * scale), int(fh * scale)), Image.LANCZOS)
    if background_path and os.path.isfile(background_path):
        bg = Image.open(background_path).convert("RGB").resize(size, Image.LANCZOS)
    else:
        bg = Image.new("RGB", size, bg_color)
    # centre paste with alpha
    x = (size[0] - fg.size[0]) // 2
    y = (size[1] - fg.size[1]) // 2
    bg.paste(fg, (x, y), fg)
    bg.save(out_path, "JPEG", quality=92)
    return {"out": out_path, "size": size, "bg": background_path or f"flat#{bg_color}",
            "fg": foreground_path, "cost_usd": 0.0}


def slideshow(image_paths: list[str], out_path: str,
              seconds_each: float = 3.0, size: tuple[int, int] = (720, 720),
              zoompan: bool = False) -> dict:
    """Stills → silent MP4 (H.264). Ken Burns if zoompan (slow on CPU).
    Default 720p static is fast; use 1080p+zoompan only for finals."""
    if not image_paths:
        raise ValueError("no images")
    total = seconds_each * len(image_paths)
    if not (VIDEO_MIN_S <= total <= VIDEO_MAX_S + 5):
        # clamp by adjusting per-image duration
        seconds_each = min(5.0, max(1.5, 12.0 / len(image_paths)))
    fps = 30
    # build filter: scale+pad each, zoompan, concat
    inputs, filters = [], []
    for i, _ in enumerate(image_paths):
        inputs += ["-loop", "1", "-t", str(seconds_each), "-i", image_paths[i]]
    for i in range(len(image_paths)):
        w, h = size
        if zoompan:
            frames = int(seconds_each * fps)
            filters.append(
                f"[{i}:v]scale={w*2}:{h*2},zoompan=z='min(zoom+0.0015,1.3)':"
                f"d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps}[v{i}]")
        else:
            filters.append(f"[{i}:v]scale={w}:{h}:force_original_aspect_ratio=increase,"
                           f"crop={w}:{h},setsar=1,fps={fps}[v{i}]")
    filters.append("".join(f"[v{i}]" for i in range(len(image_paths))) +
                   f"concat=n={len(image_paths)}:v=1:a=0[out]")
    cmd = (["ffmpeg", "-y"] + inputs +
           ["-filter_complex", ";".join(filters), "-map", "[out]",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "26",
            "-preset", "veryfast", "-movflags", "+faststart", out_path])
    r = subprocess.run(cmd, capture_output=True, timeout=180)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {r.stderr.decode()[-300:]}")
    mb = os.path.getsize(out_path) / 1e6
    return {"out": out_path, "seconds": round(seconds_each * len(image_paths), 1),
            "mb": round(mb, 1), "images": len(image_paths), "cost_usd": 0.0}


def manifest(sku: str, assets: list[dict], out_dir: str,
             pack_hash: str = "", transform_id: str = "",
             transform_version: str = "", provider: str = "",
             model: str = "", prompt_hash: str = "",
             template: str = "", cost_usd: float = 0.0,
             qc: dict | None = None) -> str:
    """Write manifest binding every output to its lineage. (dir 31)

    pack_hash + source asset hashes + transform + prompt hash + provider +
    template + output hash + cost + QC. Only immutable artifacts move
    into ReviewBundles. Product foreground never AI-invented.
    """
    import hashlib as _hl
    os.makedirs(out_dir, exist_ok=True)
    enriched = []
    for a in assets:
        a = dict(a)
        a["output_hash"] = "sha256:" + _hl.sha256(
            json.dumps(a.get("out", ""), sort_keys=True).encode()).hexdigest()[:16]
        enriched.append(a)
    path = os.path.join(out_dir, f"{sku}-media-manifest.json")
    with open(path, "w") as f:
        json.dump({
            "sku": sku,
            "pack_hash": pack_hash,
            "transform": {"id": transform_id, "version": transform_version},
            "prompt_hash": prompt_hash,
            "provider": provider, "model": model,
            "renderer_template": template,
            "cost_usd": cost_usd,
            "qc": qc or {},
            "created_at": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc).isoformat(),
            "assets": enriched,
        }, f, indent=1)
    return path


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--composite", nargs=3, metavar=("FG", "BG", "OUT"),
                    help="fg image, bg image (or 'flat'), out jpg")
    ap.add_argument("--slideshow", nargs="+", help="images + OUT=path (last arg OUT:path)")
    ap.add_argument("--size", default="2000x2000")
    args = ap.parse_args()
    if args.composite:
        fg, bg, out = args.composite
        w, h = map(int, args.size.split("x"))
        print(json.dumps(composite(fg, None if bg == "flat" else bg, out, (w, h)), indent=1))
    if args.slideshow:
        *imgs, last = args.slideshow
        out = last[4:] if last.startswith("OUT:") else "out.mp4"
        print(json.dumps(slideshow(imgs, out), indent=1))
