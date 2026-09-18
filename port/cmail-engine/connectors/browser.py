from __future__ import annotations

from .base import Observation


class BrowserConnector:
    """Boundary for Stagehand/browser automation.

    The MVP does not execute arbitrary browser writes. Keeping this adapter explicit
    lets us add deterministic Stagehand flows later without coupling browser state
    to the reconciliation engine.
    """
    kind = "browser"

    def observe(self, desired: dict) -> Observation:
        task = desired.get("task", "browser task")
        return Observation("BLOCKED", f"Browser task queued but browser worker is not enabled: {task}", executor="HUMAN",
                           human_title=desired.get("human_title") or "Complete browser-only step",
                           human_instructions=desired.get("instructions") or task,
                           human_url=desired.get("url"), estimate_seconds=int(desired.get("estimate_seconds", 60)), priority=65)
