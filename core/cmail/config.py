from __future__ import annotations

import os
from dataclasses import dataclass


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    db_url: str = os.getenv("STEVE_DB_URL", "sqlite:///./stevejobless.db")
    safe_mode: bool = _bool("STEVE_SAFE_MODE", True)
    asc_enabled: bool = _bool("STEVE_ASC_ENABLED", False)
    github_token: str | None = os.getenv("GITHUB_TOKEN") or None
    http_timeout: float = float(os.getenv("STEVE_HTTP_TIMEOUT", "5"))

    # Postiz social scheduling integration
    postiz_url: str = os.getenv("POSTIZ_URL", "")
    postiz_api_key: str = os.getenv("POSTIZ_API_KEY", "")


settings = Settings()
