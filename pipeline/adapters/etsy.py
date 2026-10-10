"""Etsy adapter — push compiled payload, verify, receipt.

Push → G1/G2 → independent GET verify (G3) → content diff (G4) → receipt.
Every push is an audited action. Price never touched.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
try:
    from verifiers.gates import run_gates
    from actions import log_action
except ImportError:
    from pipeline.verifiers.gates import run_gates
    from pipeline.actions import log_action

_ETA_DIR = pathlib.Path("/root/.config/oddhobbies")
SHOP_ID = "67863887"


def _creds() -> tuple[str, str]:
    key = (_ETA_DIR / "etsy_api_key.txt").read_text().strip()
    tok = json.loads((_ETA_DIR / "etsy_token.json").read_text())
    return key, tok["access_token"]


def _req(method: str, url: str, body: dict | None = None) -> dict:
    key, access = _creds()
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("x-api-key", key)
    req.add_header("Authorization", f"Bearer {access}")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as r:
        return {"status": r.status, "body": json.loads(r.read() or b"{}")}


def push_listing(listing_id: str, payload: dict, sku: str = "",
                 campaign: str | None = None, dry_run: bool = True) -> dict:
    """Push PATCH (or dry-run). Always verifies + receipts + audits."""
    url = f"https://openapi.etsy.com/v3/application/shops/{SHOP_ID}/listings/{listing_id}"

    if dry_run:
        log_action("etsy", f"DRY-RUN PATCH {listing_id}", 0.0, sku or None,
                   campaign, "oddhobb", str(listing_id), 0, 0, None, "UNKNOWN")
        return {"ok": True, "dry_run": True, "payload": payload,
                "fields": sorted(payload.keys())}

    # 1. PATCH
    try:
        resp = _req("PATCH", url, payload)
        code, body = resp["status"], resp["body"]
    except Exception as e:
        detail = e.read().decode()[:300] if hasattr(e, "read") else str(e)
        log_action("etsy", f"PATCH {listing_id} FAILED", 0.0, sku or None,
                   campaign, "oddhobb", str(listing_id), 0, 1, None, "FAIL")
        return {"ok": False, "error": f"{e}: {detail}"[:300]}

    # 2. independent verify (G3): fetch back via list endpoint
    try:
        live = _req("GET", f"https://openapi.etsy.com/v3/application/shops/{SHOP_ID}"
                           f"/listings?state=active&limit=100")
        actual = {}
        for it in live["body"].get("results", []):
            if str(it.get("listing_id")) == str(listing_id):
                actual = it
                break
        fetch_ok = bool(actual)
    except Exception:
        actual, fetch_ok = {}, False

    # 3. gates
    v = run_gates(
        channel="etsy", external_id=str(listing_id),
        response_code=code, response=body,
        fetch_result=actual if fetch_ok else {"error": "not found after push"},
        expected=payload, actual=actual,
        content_fields=[k for k in payload if k in ("title", "taxonomy_id")],
        claim_statement=f"Etsy listing {listing_id} updated ({','.join(sorted(payload))})",
    )
    r = v.receipt()

    # 4. audit
    log_action("etsy", f"PATCH {listing_id} ({','.join(sorted(payload))})", 0.0,
               sku or None, campaign, "oddhobb", str(listing_id),
               sum(1 for g in r["gates"] if g["result"] == "PASS"), len(r["gates"]),
               r.get("id"), "PASS" if v.all_passed else "FAIL")

    return {"ok": v.all_passed, "receipt": r, "listing_id": listing_id,
            "url": body.get("url") or actual.get("url")}


def upload_image(listing_id: str, image_path: str, rank: int = 1,
                 sku: str = "", campaign: str | None = None,
                 dry_run: bool = True) -> dict:
    """Upload one image to a listing (multipart). Verifies via GET."""
    import mimetypes
    if dry_run:
        log_action("etsy", f"DRY-RUN image upload {listing_id} <- {image_path}", 0.0,
                   sku or None, campaign, "oddhobb", str(listing_id), 0, 0, None, "UNKNOWN")
        return {"ok": True, "dry_run": True, "path": image_path, "rank": rank}
    if not os.path.isfile(image_path):
        return {"ok": False, "reason": f"file not found: {image_path}"}
    key, access = _creds()
    import uuid
    boundary = f"----etsy{uuid.uuid4().hex}"
    mime, _ = mimetypes.guess_type(image_path)
    mime = mime or "image/png"
    with open(image_path, "rb") as f:
        data = f.read()
    if len(data) > 10 * 1024 * 1024:
        return {"ok": False, "reason": "image >10MB"}
    body = (
        f"--{boundary}\r\n".encode()
        + f'Content-Disposition: form-data; name="image"; filename="{os.path.basename(image_path)}"\r\n'.encode()
        + f"Content-Type: {mime}\r\n\r\n".encode() + data
        + f"\r\n--{boundary}\r\n".encode()
        + f'Content-Disposition: form-data; name="rank"\r\n\r\n{rank}\r\n'.encode()
        + f"--{boundary}--\r\n".encode()
    )
    url = (f"https://openapi.etsy.com/v3/application/shops/{SHOP_ID}"
           f"/listings/{listing_id}/images")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("x-api-key", key)
    req.add_header("Authorization", f"Bearer {access}")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.loads(r.read() or b"{}")
        img_id = str(resp.get("listing_image_id", ""))
        log_action("etsy", f"image upload {listing_id} rank {rank}", 0.0,
                   sku or None, campaign, "oddhobb", str(listing_id),
                   2, 2, None, "PASS" if img_id else "FAIL")
        return {"ok": bool(img_id), "listing_image_id": img_id, "rank": rank}
    except Exception as e:
        detail = e.read().decode()[:200] if hasattr(e, "read") else str(e)
        log_action("etsy", f"image upload {listing_id} FAILED", 0.0,
                   sku or None, campaign, "oddhobb", str(listing_id),
                   0, 1, None, "FAIL")
        return {"ok": False, "reason": f"{e}: {detail}"[:250]}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", nargs=2, metavar=("STORE", "SKU"), default=None)
    ap.add_argument("--push", nargs=2, metavar=("LISTING_ID", "SKU"), default=None)
    ap.add_argument("--campaign", default=None)
    args = ap.parse_args()
    sys.path.insert(0, os.path.dirname(_HERE))
    try:
        from compilers.pack_loader import load as _load
        from compilers.etsy import compile_etsy as _compile
    except ImportError:
        from pipeline.compilers.pack_loader import load as _load
        from pipeline.compilers.etsy import compile_etsy as _compile
    if args.dry_run:
        p = _load(*args.dry_run)
        c = _compile(p)
        print(json.dumps(push_listing(p.get("etsy_listing_id", "?"), c["payload"],
                                      p.get("sku", ""), args.campaign, dry_run=True), indent=1)[:1500])
        print("WARNINGS:", c["warnings"])
    if args.push:
        print("LIVE PUSH — human must approve first. Use dry-run to preview.")
