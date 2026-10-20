"""YouTube compiler (L2 Upload): manifest -> videos.insert payload, DRY-RUN ONLY.

Consumes L1's output contract (final MP4 + thumb + upload-manifest.json),
runs the compliance gate, returns the exact API payload. NEVER uploads —
the executor (OAuth + human_confirm + grant) is a separate later step.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
try:
    from pipeline.yt_compliance import check_package
except ImportError:
    from yt_compliance import check_package

CATEGORY_EDUCATION = "27"


def _sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def compile_package(manifest_path: str, video_path: str,
                    thumb_path: str) -> dict:
    """manifest + files -> {ok, payload, compliance, hashes}. No network."""
    if not os.path.isfile(manifest_path):
        return {"ok": False, "reason": "manifest missing"}
    meta = json.load(open(manifest_path))
    chapters = meta.get("chapters", []) or []
    desc = str(meta.get("description", "") or "")
    if chapters:
        desc += "\n\nChapters:\n" + "\n".join(
            f"{c.get('start', '')} — {c.get('title', '')}" for c in chapters)
    body = {
        "snippet": {
            "title": str(meta.get("title", ""))[:100],
            "description": desc[:5000],
            "tags": list(meta.get("tags", []) or [])[:30],
            "categoryId": str(meta.get("categoryId", CATEGORY_EDUCATION)),
        },
        "status": {
            "privacyStatus": "unlisted",
            "madeForKids": False,
            "selfDeclaredMadeForKids": False,
        },
    }
    compliance = check_package(video_path, thumb_path, {
        "title": body["snippet"]["title"],
        "description": body["snippet"]["description"],
        "tags": body["snippet"]["tags"],
        "categoryId": body["snippet"]["categoryId"],
        "madeForKids": False,
        "privacyStatus": "unlisted",
    })
    hashes = {}
    for label, p in (("video", video_path), ("thumb", thumb_path)):
        hashes[label] = _sha(p) if os.path.isfile(p) else None
    return {"ok": compliance["ok"], "payload": body,
            "compliance": compliance, "hashes": hashes,
            "quota_note": compliance.get("quota_note", ""),
            "executor": "code-gated until OAuth creds exist; "
                        "human_confirm required"}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("video")
    ap.add_argument("thumb")
    a = ap.parse_args()
    print(json.dumps(compile_package(a.manifest, a.video, a.thumb), indent=1))
