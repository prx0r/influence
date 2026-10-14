"""R2 presigned URLs — stdlib SigV4, no boto3 (dash venv lacks it).

Audio masters archive to private R2; playback serves via 1h presigned
URLs generated server-side. Vault creds at call time, never in repo.
"""
from __future__ import annotations

import datetime
import hashlib
import hmac
import os
import subprocess
import urllib.parse


def _vault(key: str) -> str:
    r = subprocess.run(
        ["agent-vault", "vault", "credential", "get", key, "--vault",
         "oracle"], capture_output=True, text=True, timeout=15)
    return r.stdout.strip()


def _creds() -> tuple[str, str, str]:
    endpoint = (os.environ.get("R2_ENDPOINT", "") or
                _vault("CLOUDFLARE_R2_ENDPOINT"))
    access = (os.environ.get("R2_ACCESS_KEY", "") or
              _vault("CLOUDFLARE_R2_ACCESS_KEY"))
    secret = (os.environ.get("R2_SECRET_KEY", "") or
              _vault("CLOUDFLARE_R2_SECRET_KEY"))
    if not (endpoint and access and secret):
        raise RuntimeError("r2: missing endpoint/access/secret")
    return endpoint, access, secret


def _sign(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode(), hashlib.sha256).digest()


def presign_get(bucket: str, obj_key: str, expires: int = 3600) -> str:
    """Presigned HTTPS GET for a private R2 object (S3 SigV4 query auth)."""
    endpoint, access, secret = _creds()
    host = urllib.parse.urlparse(endpoint).netloc
    now = datetime.datetime.now(datetime.timezone.utc)
    amzdate = now.strftime("%Y%m%dT%H%M%SZ")
    datestamp = now.strftime("%Y%m%d")
    credential = f"{access}/{datestamp}/auto/s3/aws4_request"
    qs = (f"X-Amz-Algorithm=AWS4-HMAC-SHA256&"
          f"X-Amz-Credential={urllib.parse.quote(credential, safe='')} &"
          f"X-Amz-Date={amzdate}&X-Amz-Expires={expires}&"
          f"X-Amz-SignedHeaders=host").replace(" ", "")
    canonical = (f"GET\n/{bucket}/{urllib.parse.quote(obj_key, safe='/')}\n"
                 f"{qs}\nhost:{host}\n\nhost\nUNSIGNED-PAYLOAD")
    scope = f"{datestamp}/auto/s3/aws4_request"
    to_sign = (f"AWS4-HMAC-SHA256\n{amzdate}\n{scope}\n" +
               hashlib.sha256(canonical.encode()).hexdigest())
    k = _sign(f"AWS4{secret}".encode(), datestamp)
    k = _sign(k, "auto")
    k = _sign(k, "s3")
    k = _sign(k, "aws4_request")
    sig = hmac.new(k, to_sign.encode(), hashlib.sha256).hexdigest()
    return (f"{endpoint}/{bucket}/{urllib.parse.quote(obj_key, safe='/')}"
            f"?{qs}&X-Amz-Signature={sig}")


def audio_key(channel: str, name: str) -> str:
    safe = "".join(c if (c.isalnum() or c in "-_.") else "-"
                   for c in name)[:120]
    return f"audio/{channel or 'studio'}/{safe}"
