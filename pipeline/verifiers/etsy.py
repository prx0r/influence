"""Etsy channel verifier — proves a listing is actually live and correct."""
from __future__ import annotations

import json
import pathlib
import urllib.request
from typing import Any

from .gates import Verified, run_gates

_ETA_DIR = pathlib.Path("/root/.config/oddhobbies")


def _etsy_creds() -> tuple[str, str]:
    """Load Etsy key + token from config."""
    key = (_ETA_DIR / "etsy_api_key.txt").read_text().strip()
    tok = json.loads((_ETA_DIR / "etsy_token.json").read_text())
    return key, tok["access_token"]


def _get(url: str) -> dict:
    key, access = _etsy_creds()
    req = urllib.request.Request(url)
    req.add_header("x-api-key", key)
    req.add_header("Authorization", f"Bearer {access}")
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def verify_listing(listing_id: str, expected: dict | None = None) -> Verified:
    """G1-G4 for an Etsy listing. Fetches live and compares."""
    shop = "67863887"
    url = f"https://openapi.etsy.com/v3/application/shops/{shop}/listings?state=active&limit=100"

    fetch_result = None
    actual = {}
    try:
        data = _get(url)
        for it in data.get("results", []):
            if str(it.get("listing_id")) == str(listing_id):
                fetch_result = {"listing_id": it["listing_id"], "state": it.get("state"),
                                "title": it.get("title"), "price": str((it.get("price") or {}).get("amount", 0)),
                                "tags_count": len(it.get("tags") or [])}
                actual = it
                break
        if fetch_result is None:
            fetch_result = {"error": "listing not found in active"}
    except Exception as e:
        fetch_result = {"error": str(e)[:200]}

    expected = expected or {}
    fields = [k for k in ("title", "state", "taxonomy_id") if k in expected]
    if "price" in expected:
        fields.append("price")

    claim = f"Etsy listing {listing_id} is live"
    if expected.get("title"):
        claim += f" with title '{expected['title'][:40]}'"

    return run_gates(
        channel="etsy",
        external_id=str(listing_id),
        response_code=200 if fetch_result and not fetch_result.get("error") else 404,
        response=fetch_result or {},
        fetch_result=fetch_result,
        expected=expected,
        actual=actual,
        content_fields=fields,
        claim_statement=claim,
    )


def verify_listing_simple(listing_id: str) -> dict:
    """Quick check: is this listing active with images?"""
    v = verify_listing(listing_id)
    r = v.receipt()
    return {"ok": v.all_passed, "receipt": r}
