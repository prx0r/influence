"""Law loader. Vendored-first: influence's own fork in law/ is the kernel;
QPRIVATELY_PATH is fallback only (dev machines, CI without the vendor).

Usage at call sites (replaces the 3-line sys.path hack):
    from qp.law import use_law
    use_law()
"""
from __future__ import annotations

import os
import sys

LAW_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "law")


def use_law() -> str:
    """Ensure `import acom` resolves to the vendored fork first. Returns dir used."""
    for candidate in (LAW_DIR, os.getenv("QPRIVATELY_PATH", "/home/ubuntu/qprivately")):
        if candidate and os.path.isdir(os.path.join(candidate, "acom")):
            if candidate not in sys.path:
                sys.path.insert(0, candidate)
    if "acom" in sys.modules:
        return sys.modules["acom"].__path__[0]  # type: ignore[attr-defined]
    return LAW_DIR
