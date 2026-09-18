from __future__ import annotations

from .base import Observation


class StaticConnector:
    kind = "static"

    def observe(self, desired: dict) -> Observation:
        done = bool(desired.get("done"))
        label = desired.get("label", "Asset")
        if done:
            return Observation("READY", f"{label} marked complete", observed={"done": True})
        executor = desired.get("executor", "AUTO")
        return Observation("MISSING", f"{label} missing", executor=executor,
                           human_title=desired.get("human_title") or f"Finish {label}",
                           human_instructions=desired.get("instructions") or f"Complete {label} and mark it done in the passport.",
                           human_url=desired.get("url"), estimate_seconds=int(desired.get("estimate_seconds", 120)),
                           priority=int(desired.get("priority", 50)))
