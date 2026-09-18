"""Actuality: three-valued truth ported from pmail qp/kernel patterns (ISC, prx0r/pmail).
FALSE dominates UNKNOWN dominates TRUE. Timeouts and ambiguity map to UNKNOWN, never FALSE.
Sits alongside engine statuses; statuses say what was observed, actuality says what is proven."""
from __future__ import annotations

from enum import Enum


class Actuality(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"


def and_dag(*items: Actuality) -> Actuality:
    if any(a is Actuality.FALSE for a in items):
        return Actuality.FALSE
    if any(a is Actuality.UNKNOWN for a in items):
        return Actuality.UNKNOWN
    return Actuality.TRUE


# Engine status -> actuality. MISSING means not observed either way: UNKNOWN, not FALSE.
STATUS_ACTUALITY = {
    "READY": Actuality.TRUE,
    "MISSING": Actuality.UNKNOWN,
    "BLOCKED": Actuality.FALSE,
    "UNKNOWN": Actuality.UNKNOWN,
    "ERROR": Actuality.UNKNOWN,
}


def actuality_of_status(status: str) -> Actuality:
    return STATUS_ACTUALITY.get(status, Actuality.UNKNOWN)
