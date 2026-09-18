from __future__ import annotations

from pathlib import Path

from .base import Observation


class LocalArtifactConnector:
    kind = "local_artifact"

    def observe(self, desired: dict) -> Observation:
        path = Path(desired.get("path", ""))
        if not str(path):
            return Observation("ERROR", "Artifact path missing")
        if path.exists() and path.stat().st_size > 0:
            return Observation("READY", f"Generated artifact exists: {path}", observed={"path": str(path), "bytes": path.stat().st_size})
        return Observation("MISSING", f"Artifact not generated yet: {path}", executor="AUTO", observed={"path": str(path)})

    def apply(self, desired: dict) -> dict:
        path = Path(desired["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        content = desired.get("content", "")
        path.write_text(content)
        return {"ok": True, "path": str(path), "bytes": len(content.encode())}
