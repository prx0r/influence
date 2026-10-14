#!/usr/bin/env python3
"""Ship studio voice bank to private R2, prune local disk.

Policy: masters + clips older than --days (default 3) upload to
audio/<channel>/, HEAD-verified, then local MP3 deleted (meta .json kept
with r2_key — dash serves playback via presigned URLs). Recent clips stay
local for instant play. Dry-run default. $0 (R2 negligible).
"""
import argparse
import glob
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "pipeline"))

VOICE = "/root/sleepdraw/runs/studio/voice"
BUCKET = os.environ.get("R2_BUCKET", "blog-video-assets")


def _s3():
    import subprocess

    def vault(k):
        r = subprocess.run(
            ["agent-vault", "vault", "credential", "get", k, "--vault",
             "oracle"], capture_output=True, text=True, timeout=15)
        return r.stdout.strip()

    import boto3
    from botocore.client import Config
    return boto3.client(
        "s3", endpoint_url=os.environ.get("R2_ENDPOINT") or
        vault("CLOUDFLARE_R2_ENDPOINT"),
        aws_access_key_id=os.environ.get("R2_ACCESS_KEY") or
        vault("CLOUDFLARE_R2_ACCESS_KEY"),
        aws_secret_access_key=os.environ.get("R2_SECRET_KEY") or
        vault("CLOUDFLARE_R2_SECRET_KEY"),
        region_name="auto", config=Config(signature_version="s3v4"))


def ship(days: int = 3, dry_run: bool = True, channel: str = "studio",
         min_bytes: int = 0) -> dict:
    from r2_presign import audio_key
    s = _s3()
    cutoff = time.time() - days * 86400
    shipped, skipped, errors = [], [], []
    for mp3 in sorted(glob.glob(os.path.join(VOICE, "*.mp3"))):
        name = os.path.basename(mp3)
        meta_p = mp3 + ".json"
        meta = {}
        if os.path.isfile(meta_p):
            try:
                meta = json.load(open(meta_p))
            except Exception:
                pass
        if meta.get("r2_key"):
            skipped.append(name + " (already shipped)")
            continue
        size = os.path.getsize(mp3)
        if size < min_bytes:
            skipped.append(name + " (under min_bytes)")
            continue
        if os.path.getmtime(mp3) > cutoff:
            skipped.append(name + " (fresh)")
            continue
        key = audio_key(meta.get("channel", channel)
                        if isinstance(meta.get("channel"), str) else channel,
                        name)
        if dry_run:
            shipped.append({"file": name, "key": key, "dry_run": True,
                            "bytes": os.path.getsize(mp3)})
            continue
        try:
            with open(mp3, "rb") as f:
                s.put_object(Bucket=BUCKET, Key=key, Body=f,
                             ContentType="audio/mpeg")
            head = s.head_object(Bucket=BUCKET, Key=key)
            if head.get("ContentLength") != os.path.getsize(mp3):
                raise RuntimeError("size mismatch after upload")
            meta["r2_key"] = key
            meta["r2_bucket"] = BUCKET
            meta["shipped_at"] = int(time.time())
            json.dump(meta, open(meta_p, "w"), indent=1)
            os.remove(mp3)
            shipped.append({"file": name, "key": key,
                            "bytes": meta.get("shipped_bytes", 0)})
        except Exception as e:  # noqa: BLE001 — one file can't kill the run
            errors.append(f"{name}: {e}"[:200])
    return {"ok": not errors, "dry_run": dry_run, "shipped": shipped,
            "skipped": skipped, "errors": errors}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=3)
    ap.add_argument("--live", action="store_true",
                    help="actually upload+prune (default dry-run)")
    ap.add_argument("--channel", default="studio")
    print(json.dumps(ship(ap.parse_args().days, not ap.parse_args().live,
                          ap.parse_args().channel), indent=1)[:2000])
