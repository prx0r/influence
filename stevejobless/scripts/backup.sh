#!/bin/bash
# Nightly SQLite → R2 backup for stevejobless. Online-safe via sqlite3 .backup.
# Restore: download object, stop service, replace file, start service.
set -u
DB=${STEVE_DB:-/root/stevejobless.db}
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
TMP="/tmp/steve-backup-$STAMP.db"
R2_BUCKET=${R2_BUCKET:-cmail-raw}
KEY="backups/stevejobless/$STAMP.db"

python3 - "$DB" "$TMP" <<'EOF'
import sqlite3, sys
src, dst = sys.argv[1], sys.argv[2]
s = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
d = sqlite3.connect(dst)
with d:
    s.backup(d)
d.close(); s.close()
print("snapshot ok")
EOF
if [ "${R2_S3_ENDPOINT:-}" ] && [ "${R2_S3_ACCESS_KEY:-}" ] && [ "${R2_S3_SECRET_KEY:-}" ]; then
  python3 - "$TMP" "$R2_BUCKET" "$KEY" <<'EOF'
import os, sys
from urllib.request import Request, urlopen
import hashlib, hmac, datetime
# minimal S3 PUT (SigV4) — no boto dependency
src, bucket, key = sys.argv[1], sys.argv[2], sys.argv[3]
endpoint = os.environ["R2_S3_ENDPOINT"].rstrip("/")
ak, sk = os.environ["R2_S3_ACCESS_KEY"], os.environ["R2_S3_SECRET_KEY"]
data = open(src, "rb").read()
now = datetime.datetime.now(datetime.timezone.utc)
amz = now.strftime("%Y%m%dT%H%M%SZ")
ds = now.strftime("%Y%m%d")
host = endpoint.split("://", 1)[1]
url = f"{endpoint}/{bucket}/{key}"
h = hashlib.sha256(data).hexdigest()
creq = f"PUT\n/{bucket}/{key}\n\ncontent-type:application/octet-stream\nhost:{host}\nx-amz-content-sha256:{h}\nx-amz-date:{amz}\n\ncontent-type;host;x-amz-content-sha256;x-amz-date\n{h}"
ss = f"AWS4-HMAC-SHA256\n{amz}\n{ds}/auto/s3/aws4_request\n" + hashlib.sha256(creq.encode()).hexdigest()
def H(k, m):
    return hmac.new(k, m.encode() if isinstance(m, str) else m, hashlib.sha256).digest()
sig = hmac.new(H(H(H(H(("AWS4" + sk).encode(), ds), "auto"), "s3"), "aws4_request"), ss.encode(), hashlib.sha256).hexdigest()
req = Request(url, data=data, method="PUT", headers={
    "Content-Type": "application/octet-stream", "x-amz-date": amz,
    "x-amz-content-sha256": h,
    "Authorization": f"AWS4-HMAC-SHA256 Credential={ak}/{ds}/auto/s3/aws4_request, SignedHeaders=content-type;host;x-amz-content-sha256;x-amz-date, Signature={sig}"})
with urlopen(req, timeout=120) as resp:
    print("uploaded", resp.status, key)
EOF
else
  mkdir -p /root/backups && cp "$TMP" "/root/backups/stevejobless-$STAMP.db" && echo "local backup /root/backups/stevejobless-$STAMP.db (R2 env unset)"
fi
rm -f "$TMP"
# prune local copies older than 14d
find /root/backups -name "stevejobless-*.db" -mtime +14 -delete 2>/dev/null
