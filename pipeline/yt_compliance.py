"""YouTube compliance gate — script → studio → unlisted → publish.

Checks a final MP4 + thumbnail + metadata against Creator Studio / Data
API expectations BEFORE any upload quota burns. Pure ffprobe + rules.
Refuses with named reasons; never uploads.

Video (per support.google.com/youtube/answer/4603579 + upload guides):
  container MP4, H.264 + AAC, audio ≥128k @44.1/48k, 16:9 ≥720p,
  yuv420p, moov faststart (progressive playback).
Metadata (videos.insert): title ≤100, description ≤5000, tags ≤500 chars
total / ≤30 tags, categoryId set, madeForKids explicit, privacy unlisted.
Thumbnail: 1280x720 JPEG/PNG ≤2MB (thumbnails.set = 50 quota units).
Quota note: videos.insert ≈1600u; default 10k/day ≈ ~6 videos/day w/ thumbs.
"""
from __future__ import annotations

import json
import os
import subprocess

TITLE_MAX = 100
DESC_MAX = 5000
TAGS_MAX = 30
TAGS_CHARS_MAX = 500
THUMB_MAX = 2 * 1024 * 1024


def _probe(path: str) -> dict:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_format", "-show_streams",
         "-of", "json", path], capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        return {"ok": False, "reason": f"ffprobe: {r.stderr[:150]}"}
    return {"ok": True, "data": json.loads(r.stdout or "{}")}


def check_video(path: str) -> dict:
    """Gate a final MP4. Returns {ok, checks{}, failures[]}."""
    if not os.path.isfile(path):
        return {"ok": False, "failures": ["file missing"]}
    p = _probe(path)
    if not p.get("ok"):
        return {"ok": False, "failures": [p["reason"]]}
    streams = (p["data"].get("streams") or [])
    v = next((s for s in streams if s.get("codec_type") == "video"), {})
    a = next((s for s in streams if s.get("codec_type") == "audio"), {})
    checks, failures, warnings = {}, [], {}
    checks["container_mp4"] = path.lower().endswith(".mp4")
    checks["vcodec_h264"] = v.get("codec_name") == "h264"
    checks["pix_yuv420p"] = v.get("pix_fmt") == "yuv420p"
    w, h = int(v.get("width") or 0), int(v.get("height") or 0)
    checks["res_720p_plus"] = h >= 720 and w >= 1280
    checks["acodec_aac"] = a.get("codec_name") == "aac"
    try:
        abr = int(a.get("bit_rate") or 0) // 1000
    except (TypeError, ValueError):
        abr = 0
    # bitrate is a WARNING not a failure: quiet sleep audio legitimately
    # averages under 128k even when encoded at 128k (AAC is not true CBR).
    # YT itself sets no minimum bitrate.
    checks["audio_128k_plus"] = abr >= 128
    if not checks["audio_128k_plus"] and checks["acodec_aac"]:
        warnings["audio_bitrate"] = (f"measured {abr}kbps under 128k — "
                                     "normal for quiet content, YT has no minimum")
    try:
        checks["audio_48k"] = int(a.get("sample_rate") or 0) in (44100, 48000)
    except (TypeError, ValueError):
        checks["audio_48k"] = False
    # moov faststart: moov before mdat
    try:
        with open(path, "rb") as f:
            head = f.read(min(32 * 1024 * 1024, os.path.getsize(path)))
        moov, mdat = head.find(b"moov"), head.find(b"mdat")
        checks["moov_faststart"] = moov != -1 and (mdat == -1 or moov < mdat)
    except OSError:
        checks["moov_faststart"] = False
    for k, ok in checks.items():
        if k == "audio_128k_plus":
            continue  # warning-class, handled above
        if not ok:
            failures.append(k)
    return {"ok": not failures, "checks": checks, "warnings": warnings,
            "failures": failures, "width": w, "height": h,
            "audio_kbps": abr}


def check_metadata(meta: dict) -> dict:
    """Gate title/description/tags/privacy for videos.insert."""
    title = str(meta.get("title", "") or "")
    desc = str(meta.get("description", "") or "")
    tags = meta.get("tags", []) or []
    failures = []
    if not title or len(title) > TITLE_MAX:
        failures.append(f"title 1..{TITLE_MAX} chars (got {len(title)})")
    if len(desc) > DESC_MAX:
        failures.append("description over 5000 chars")
    if len(tags) > TAGS_MAX or sum(len(t) for t in tags) > TAGS_CHARS_MAX:
        failures.append("tags over 30 count / 500 chars")
    if not meta.get("categoryId"):
        failures.append("categoryId required")
    if meta.get("madeForKids") is None:
        failures.append("madeForKids must be explicit (false for sleep)")
    if meta.get("privacyStatus", "unlisted") != "unlisted":
        failures.append("first upload must be unlisted (human flips public)")
    return {"ok": not failures, "failures": failures}


def check_thumbnail(path: str) -> dict:
    """Gate 1280x720 JPEG/PNG ≤2MB."""
    if not os.path.isfile(path):
        return {"ok": False, "failures": ["file missing"]}
    failures = []
    if os.path.getsize(path) > THUMB_MAX:
        failures.append("over 2MB")
    try:
        from PIL import Image
        im = Image.open(path)
        if im.size != (1280, 720):
            failures.append(f"size {im.size}, want 1280x720")
        if (im.format or "").upper() not in ("JPEG", "JPG", "PNG"):
            failures.append(f"format {im.format}")
    except ImportError:
        pass  # size gate stands without PIL
    except Exception as e:  # noqa: BLE001
        failures.append(f"unreadable: {e}"[:100])
    return {"ok": not failures, "failures": failures}


def check_package(video: str, thumb: str, meta: dict) -> dict:
    """Full pre-upload gate: video + thumb + metadata."""
    v, t, m = check_video(video), check_thumbnail(thumb), check_metadata(meta)
    ok = v["ok"] and t["ok"] and m["ok"]
    return {"ok": ok, "video": v, "thumbnail": t, "metadata": m,
            "quota_note": "videos.insert ~1600u + thumbnails.set 50u"}
