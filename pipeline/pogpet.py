"""pogpet bridge — read across the boundary, never duplicate.

- Transforms: read /root/pogpet/transforms/*.json directly
- Suppliers: read /root/pogpet/catalog/suppliers.json technical fields
- MCP: call pogpet tools over HTTP (audited like everything else)

influence never writes to pogpet files. pogpet never writes to influence DB.
See docs/pipeline/POGPET-INTEGRATION.md.
"""
from __future__ import annotations

import json
import os

POGPET_ROOT = os.getenv("POGPET_ROOT", "/root/pogpet")
TRANSFORMS_DIR = os.path.join(POGPET_ROOT, "transforms")
SUPPLIERS_PATH = os.path.join(POGPET_ROOT, "catalog", "suppliers.json")
POGPET_MCP = os.getenv("POGPET_MCP", "https://oddhobb.com/mcp")

# pogpet slug → influence slug (join key for supplier sync)
SUPPLIER_MAP = {
    "jlc3dp": "jlc",
    "printie": "printie",
    "makerfabs": "makerfabs",
    "elecrow": "elecrow",
    "seeed": "seeed",
    "nextsmartship": "nextsmartship",
    "china-fulfillment": "china-fulfillment",
    "onebookprint": "onebookprint",
    "makr3d": "makr3d",
    "prodigi": "prodigi",
}


def load_transforms() -> dict[str, dict]:
    """Read pogpet transforms/*.json. Returns {id: transform} (latest version)."""
    out: dict[str, dict] = {}
    if not os.path.isdir(TRANSFORMS_DIR):
        return out
    for fn in sorted(os.listdir(TRANSFORMS_DIR)):
        if not fn.endswith(".json"):
            continue
        try:
            with open(os.path.join(TRANSFORMS_DIR, fn)) as f:
                t = json.load(f)
        except (OSError, ValueError):
            continue
        if not isinstance(t, dict) or not t.get("id"):
            continue
        cur = out.get(t["id"])
        if cur is None or int(t.get("version", 1)) > int(cur.get("version", 1)):
            t["_file"] = fn
            out[t["id"]] = t
    return out


def list_transforms(status: str | None = None) -> list[dict]:
    ts = load_transforms()
    out = []
    for tid, t in sorted(ts.items()):
        if status and t.get("status") != status:
            continue
        out.append({
            "id": tid, "version": t.get("version"),
            "status": t.get("status"), "capability": t.get("capability"),
            "products": t.get("products", []),
            "qc": list((t.get("qc") or {}).keys()),
        })
    return out


def transform_qc(transform_id: str) -> dict:
    """QC block for a transform → maps to our image.py gates."""
    ts = load_transforms()
    t = ts.get(transform_id, {})
    return t.get("qc", {})


def load_pogpet_suppliers() -> dict:
    """Read pogpet catalog/suppliers.json technical truth."""
    try:
        with open(SUPPLIERS_PATH) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def supplier_tech(pogpet_slug: str) -> dict:
    """Technical fields for one supplier: processes, upload_rules, shipping."""
    d = load_pogpet_suppliers()
    s = d.get(pogpet_slug, {})
    return {
        "name": s.get("name", ""),
        "site": s.get("site", ""),
        "processes": s.get("processes", []),
        "ships_from": s.get("ships_from", ""),
        "dropship": s.get("dropship"),
        "upload_rules": s.get("upload_rules", ""),
        "shipping_known": s.get("shipping_known", {}),
        "status": s.get("status", ""),
        "role": s.get("role", ""),
    }


def call_mcp(tool: str, args: dict, timeout: int = 60) -> dict:
    """Call a pogpet MCP tool. Returns response dict. Caller verifies + receipts."""
    import urllib.request
    body = json.dumps({"tool": tool, "args": args, "actor": "influence-dash"}).encode()
    req = urllib.request.Request(POGPET_MCP, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "influence-dash/1.0")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read() or b"{}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--transforms", action="store_true")
    ap.add_argument("--suppliers", action="store_true")
    ap.add_argument("--qc", default=None)
    args = ap.parse_args()
    if args.transforms:
        for t in list_transforms():
            print(f"{t['id']:25} v{t['version']} {t['status']:10} {t['capability']:20} → {t['products']}")
    if args.qc:
        print(json.dumps(transform_qc(args.qc), indent=1))
    if args.suppliers:
        for ps in sorted(load_pogpet_suppliers()):
            print(f"{ps:20} → {SUPPLIER_MAP.get(ps, '?')}")
