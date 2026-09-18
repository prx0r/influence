from __future__ import annotations

from typing import Any

from .base import Observation
from .postiz import PostizConnector


class PublisherConnector:
    """Publishing path via Postiz. Drafts are data (counted from desired);
    the publish action itself always stays behind the human decide gate.
    READY means the path is open, never that anything was sent."""

    kind = "publisher"

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self._postiz = PostizConnector(base_url, api_key)

    def observe(self, desired: dict[str, Any]) -> Observation:
        platforms = [str(p).lower() for p in desired.get("platforms", []) if p]
        drafts = desired.get("drafts", [])
        ndrafts = len(drafts) if isinstance(drafts, list) else 0
        integrations = self._postiz._list_integrations()
        if not integrations:
            return Observation(
                "MISSING", f"Publisher not wired ({ndrafts} drafts queued, publishing gated)",
                observed={"drafts": ndrafts, "platforms": platforms},
                executor="HUMAN",
                human_title="Connect Postiz publisher",
                human_instructions="Point POSTIZ_URL + POSTIZ_API_KEY at a running Postiz, connect channels, then re-run reconcile. Drafts stay drafts until you approve them.",
                estimate_seconds=300, priority=60)
        connected = {str(i.get("identifier", "")).lower() for i in integrations
                     if not i.get("disabled")}
        missing = [p for p in platforms if p not in connected]
        if missing:
            return Observation(
                "MISSING", f"Publisher open, missing channels: {', '.join(missing)}",
                observed={"drafts": ndrafts, "connected": sorted(connected), "missing": missing},
                executor="HUMAN",
                human_title=f"Connect channels: {', '.join(missing)}",
                human_instructions="Add the missing channels in Postiz, then re-run reconcile.",
                estimate_seconds=180, priority=60)
        return Observation(
            "READY", f"Publisher open ({len(connected)} channels, {ndrafts} drafts, sends gated)",
            observed={"drafts": ndrafts, "connected": sorted(connected)})
