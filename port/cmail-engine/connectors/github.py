from __future__ import annotations

import httpx

from .base import Observation
from ..config import settings


class GitHubConnector:
    kind = "github_repo"

    def observe(self, desired: dict) -> Observation:
        repo = desired.get("repo")
        if not repo:
            return Observation("MISSING", "No GitHub repository configured", executor="HUMAN",
                               human_title="Choose a GitHub repository",
                               human_instructions="Create or choose the canonical GitHub repository, then add owner/name to the Studio Passport.",
                               human_url="https://github.com/new", estimate_seconds=90, priority=85)
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if settings.github_token:
            headers["Authorization"] = f"Bearer {settings.github_token}"
        try:
            with httpx.Client(timeout=settings.http_timeout, headers=headers) as client:
                r = client.get(f"https://api.github.com/repos/{repo}")
            if r.status_code == 200:
                data = r.json()
                return Observation("READY", f"Repository {repo} exists",
                                   observed={"repo": repo, "default_branch": data.get("default_branch"), "private": data.get("private"), "archived": data.get("archived")})
            if r.status_code == 404:
                return Observation("MISSING", f"Repository {repo} not found", executor="HUMAN",
                                   human_title=f"Create {repo}",
                                   human_instructions=f"Create the repository {repo}. Steve will detect it automatically on the next reconcile.",
                                   human_url="https://github.com/new", estimate_seconds=60, priority=80)
            return Observation("UNKNOWN", f"GitHub returned HTTP {r.status_code}", observed={"http_status": r.status_code})
        except Exception as exc:
            return Observation("UNKNOWN", f"GitHub inspection unavailable: {exc}", observed={"offline": True})
