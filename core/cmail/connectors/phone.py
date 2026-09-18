from __future__ import annotations

from typing import Any

from .base import Observation

# Capability matrix. Per-direction tristate: True / False / "UNKNOWN".
# UNKNOWN means unvalidated — it never satisfies a TRUE requirement.
# Status experimental = no live acceptance yet; validated = dated evidence.
PROVIDERS: list[dict[str, Any]] = [
    {"name": "silentlink", "status": "validated",
     "class": "PSEUDONYMOUS_BRIDGE",
     "caps": {"sms_in": True, "sms_out": False, "voice_in": False,
              "voice_out": False, "data": True},
     "note": "Inbound SMS + data only. Never a full phone."},
    {"name": "pikasim", "status": "experimental",
     "class": "PSEUDONYMOUS_BRIDGE",
     "caps": {"sms_in": "UNKNOWN", "sms_out": "UNKNOWN", "voice_in": "UNKNOWN",
              "voice_out": "UNKNOWN", "data": "UNKNOWN"},
     "note": "Advertises voice+SMS+data; promote only after live acceptance."},
    {"name": "telnyx", "status": "validated",
     "class": "IDENTITY_BRIDGED",
     "caps": {"sms_in": True, "sms_out": True, "voice_in": True,
              "voice_out": True, "data": False},
     "note": "Full PSTN but KYC. Strict policies must reject it."},
]

CLASS_ORDER = ["ANON_CORE", "PSEUDONYMOUS_BRIDGE", "IDENTITY_BRIDGED"]


def select_bridge(require: list[str],
                  max_class: str = "PSEUDONYMOUS_BRIDGE") -> dict[str, Any]:
    """Hard-filter selection. Returns eligible routes plus rejected with
    reasons. Never silently falls back to a more invasive provider."""
    eligible, rejected = [], []
    for p in PROVIDERS:
        reasons = []
        if CLASS_ORDER.index(p["class"]) > CLASS_ORDER.index(max_class):
            reasons.append(f"class {p['class']} exceeds max {max_class}")
        for cap in require:
            v = p["caps"].get(cap, "UNKNOWN")
            if v is not True:
                reasons.append(f"{cap} is {v}, required TRUE")
        if reasons:
            rejected.append({"provider": p["name"], "reasons": reasons})
        else:
            eligible.append({"provider": p["name"], "status": p["status"],
                             "class": p["class"], "note": p["note"]})
    return {"eligible": eligible, "rejected": rejected}


class PhoneConnector:
    """Number provisioning via hard-filter bridge selection. A recorded
    resource ref without live readback stays UNKNOWN, never READY."""

    kind = "number"

    def observe(self, desired: dict) -> Observation:
        require = [c for c in desired.get("capabilities", ["sms_in"]) if isinstance(c, str)]
        max_class = desired.get("max_class", "PSEUDONYMOUS_BRIDGE")
        if max_class not in CLASS_ORDER:
            max_class = "IDENTITY_BRIDGED"
        ref = desired.get("resource_ref")
        if ref:
            return Observation("UNKNOWN", f"Number {ref} recorded, awaiting live readback",
                               observed={"resource_ref": ref, "require": require},
                               executor="HUMAN",
                               human_title="Verify number capabilities",
                               human_instructions=f"Run an independent nonce round-trip against {ref} for {', '.join(require)}. Provider claims alone never close this.",
                               estimate_seconds=180, priority=65)
        try:
            sel = select_bridge(require, max_class)
        except Exception as exc:
            return Observation("UNKNOWN", f"Bridge selection failed: {exc}",
                               observed={"require": require})
        if not sel["eligible"]:
            return Observation("BLOCKED", "No eligible bridge under policy",
                               observed={"require": require, "max_class": max_class,
                                         "rejected": sel["rejected"]},
                               executor="HUMAN",
                               human_title="Loosen policy or add a provider",
                               human_instructions="Every candidate violates the privacy policy or lacks a required direction. No fallback was taken.",
                               estimate_seconds=300, priority=85)
        best = sel["eligible"][0]["provider"]
        return Observation("MISSING", f"Provision number via {best} ({', '.join(require)})",
                           observed={"require": require, "eligible": sel["eligible"]},
                           executor="HUMAN",
                           human_title=f"Provision number via {best}",
                           human_instructions=f"Fund and provision through {best} with a bounded grant. Record the resource ref back here; capability is proven by nonce round-trip, not by the purchase receipt.",
                           estimate_seconds=600, priority=70)
