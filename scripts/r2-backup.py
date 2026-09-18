#!/usr/bin/env python3
"""Nightly R2 backup of append-only logs + DB snapshots. boto3 import is lazy
so --dry-run works anywhere with stdlib only.

Env: R2_ENDPOINT, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET
(default influence-backups). Prints only file names + bytes, never creds.
"""
import datetime
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = ["dash/receipts.jsonl", "dash/rewards.jsonl", "dash/drafts.jsonl",
         "dash/quarantine.jsonl", "dash/influence.db", "dash/decisions.db"]


def manifest(paths):
    items = []
    for rel in paths:
        full = os.path.join(ROOT, rel)
        if not os.path.exists(full):
            continue
        with open(full, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()
        items.append({"path": rel, "bytes": os.path.getsize(full),
                      "sha256": digest})
    day = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    return {"day": day, "files": items}


def main():
    dry = "--dry-run" in sys.argv
    man = manifest(FILES)
    man["mode"] = "dry-run" if dry else "upload"
    if dry:
        print(json.dumps(man, indent=1))
        return 0
    import boto3  # noqa: E402
    endpoint = os.environ["R2_ENDPOINT"]
    bucket = os.environ.get("R2_BUCKET", "influence-backups")
    s3 = boto3.client("s3", endpoint_url=endpoint,
                      aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
                      aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"])
    try:
        s3.head_bucket(Bucket=bucket)
    except Exception:
        s3.create_bucket(Bucket=bucket)
    prefix = f"influence/{man['day']}/"
    for item in man["files"]:
        with open(os.path.join(ROOT, item["path"]), "rb") as f:
            s3.upload_fileobj(f, bucket, prefix + item["path"].replace("/", "_"))
        print(f"backed up {item['path']} ({item['bytes']}b)")
    s3.put_object(Bucket=bucket, Key=prefix + "manifest.json",
                  Body=json.dumps(man, indent=1).encode())
    print(f"manifest for {man['day']}: {len(man['files'])} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
