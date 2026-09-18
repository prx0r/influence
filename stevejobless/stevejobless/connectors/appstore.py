from __future__ import annotations

import json
import shutil
import subprocess

from .base import Observation
from ..config import settings


class AppStoreConnector:
    kind = "app_store"

    def observe(self, desired: dict) -> Observation:
        bundle_id = desired.get("bundle_id")
        app_name = desired.get("app_name")
        app_id = desired.get("app_store_id")
        if not bundle_id:
            return Observation("MISSING", "Bundle identifier missing", executor="HUMAN",
                               human_title="Choose bundle identifier",
                               human_instructions="Choose the canonical reverse-DNS bundle identifier and add it to the passport.",
                               estimate_seconds=30, priority=90)
        if not settings.asc_enabled:
            if app_id:
                return Observation("UNKNOWN", "App Store ID configured; enable asc-cli to verify live state",
                                   observed={"bundle_id": bundle_id, "app_store_id": app_id, "asc_enabled": False})
            return Observation("MISSING", "App Store record is not linked", executor="HUMAN",
                               human_title=f"Create App Store record for {app_name or bundle_id}",
                               human_instructions="Install/configure asc-cli, create the App Store Connect record, then add app_store_id to the passport. Legal agreements and first-time account setup stay human-controlled.",
                               human_url="https://appstoreconnect.apple.com/apps", estimate_seconds=180, priority=100)
        if not shutil.which("asc"):
            return Observation("BLOCKED", "STEVE_ASC_ENABLED=1 but asc binary is not installed", executor="HUMAN",
                               human_title="Install asc-cli",
                               human_instructions="Run `brew install asccli`, authenticate with `asc auth login`, then reconcile again.",
                               human_url="https://github.com/tddworks/asc-cli", estimate_seconds=120, priority=95)
        try:
            proc = subprocess.run(["asc", "apps", "list"], text=True, capture_output=True, timeout=30)
            if proc.returncode != 0:
                return Observation("BLOCKED", f"asc-cli failed: {proc.stderr.strip()[:300]}", executor="HUMAN",
                                   human_title="Fix App Store Connect authentication",
                                   human_instructions="Run `asc auth check`; re-authenticate if needed, then reconcile.",
                                   estimate_seconds=90, priority=100)
            data = json.loads(proc.stdout)
            apps = data if isinstance(data, list) else data.get("data") or data.get("apps") or []
            match = None
            for item in apps:
                attrs = item.get("attributes", item)
                if str(item.get("id")) == str(app_id) or attrs.get("bundleId") == bundle_id or attrs.get("bundle_id") == bundle_id:
                    match = item
                    break
            if match:
                return Observation("READY", "App Store Connect record found", observed={"app": match, "bundle_id": bundle_id})
            return Observation("MISSING", "No matching App Store Connect record found", executor="HUMAN",
                               human_title=f"Create App Store record for {app_name or bundle_id}",
                               human_instructions="Create the app record in App Store Connect (or via asc iris where appropriate), then reconcile.",
                               human_url="https://appstoreconnect.apple.com/apps", estimate_seconds=180, priority=100)
        except Exception as exc:
            return Observation("ERROR", f"Could not query asc-cli: {exc}")
