"""Modules as a derived QP concept: namespaces with teeth.

A module is NOT a kernel primitive (SPEC's seven objects are enough).
It is a registered mapping — claim-domain + allowed gate set — plus a
scope check that FAILS any receipt carrying gates outside its module.
That makes module membership provable with existing primitives: no
receipt-shape change, no law edit, new-versioned-extension style.

To add a module: add one entry below. To move a claim family: change its
domain mapping here (new mapping, old receipts verify forever).
"""
from __future__ import annotations

BASE_GATES = ["evidence-fresh-v1", "no-duplicate-v1", "claim-resolved-v1"]

MODULES = {
    "provision": {
        "description": "idea → name → domain → email → phone → socials → endpoint",
        "domains": ["influence.project", "influence.provision", "influence.targets",
                    "influence.sweep", "influence.tunnel", "influence.experiment"],
        "gates": BASE_GATES + ["two-sources-v1"],
    },
    "studio": {
        "description": "content factory: sets, judges, lineages, rewards",
        "domains": ["influence.reward", "influence.lineage"],
        "gates": BASE_GATES,
    },
    "ledger": {
        "description": "money + privacy: spends, grants, attested runs",
        "domains": ["influence.spend"],
        "gates": BASE_GATES,
    },
    "venue": {
        "description": "rooms, events, bookings (reserved, no receipts yet)",
        "domains": [],
        "gates": BASE_GATES,
    },
}


def module_of_domain(domain: str) -> str | None:
    for mod, spec in MODULES.items():
        if domain in spec["domains"]:
            return mod
    return None


def scope_check(receipt: dict) -> dict:
    """PASS iff the receipt's claim domain is registered AND every executed
    gate id belongs to that module's set. A provisioning receipt carrying
    studio-only gates (or vice versa) fails scope — cross-module
    masquerading is a FAIL, not a warning."""
    proposal = receipt.get("proposal", {}) or {}
    claim = proposal.get("claim", proposal) or {}
    domain = claim.get("domain", "?")
    mod = module_of_domain(domain)
    if mod is None:
        return {"ok": False, "module": None, "reason": f"unregistered domain {domain}"}
    allowed = set(MODULES[mod]["gates"])
    seen = [g.get("id", "?") for g in receipt.get("gates", [])]
    foreign = [g for g in seen if g not in allowed]
    if foreign:
        return {"ok": False, "module": mod, "reason": f"gates outside {mod}: {foreign}"}
    return {"ok": True, "module": mod, "reason": f"{len(seen)} gates within {mod}"}
