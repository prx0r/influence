"""Privacy calculus ported from pmail privacy/types patterns (ISC, prx0r/pmail).
Composition degrades monotonically, never improves. Policy gates max class + forbidden traits."""
from __future__ import annotations

from dataclasses import dataclass, field

CLASS_ORDER = ["ANON_CORE", "PSEUDONYMOUS_BRIDGE", "IDENTITY_BRIDGED"]
KNOWN_TRAITS = {"legal_identity", "phone", "email", "card_payment", "google_oauth", "pstn_kyc"}


def compose(*classes: str) -> str:
    """Worst class wins. Unknown class names fail closed to IDENTITY_BRIDGED."""
    idx = 0
    for c in classes:
        if c not in CLASS_ORDER:
            return "IDENTITY_BRIDGED"
        idx = max(idx, CLASS_ORDER.index(c))
    return CLASS_ORDER[idx]


@dataclass(frozen=True)
class PrivacyPolicy:
    max_class: str = "PSEUDONYMOUS_BRIDGE"
    forbid: tuple[str, ...] = ()


@dataclass
class PrivacyDecision:
    allowed: bool
    resulting_class: str
    violations: list[str] = field(default_factory=list)


def evaluate(resulting_class: str, traits: list[str], policy: PrivacyPolicy) -> PrivacyDecision:
    violations = []
    if resulting_class not in CLASS_ORDER or CLASS_ORDER.index(resulting_class) > CLASS_ORDER.index(policy.max_class):
        violations.append(f"class {resulting_class} exceeds max {policy.max_class}")
    for t in traits:
        if t in policy.forbid:
            violations.append(f"forbidden trait: {t}")
        elif t not in KNOWN_TRAITS:
            violations.append(f"unknown trait (fail closed): {t}")
    return PrivacyDecision(allowed=not violations, resulting_class=resulting_class, violations=violations)
