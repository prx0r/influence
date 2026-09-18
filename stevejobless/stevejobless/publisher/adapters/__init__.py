"""Platform adapter registry."""
from __future__ import annotations

from typing import Protocol

from . import bluesky, facebook, instagram, linkedin, tiktok, twitter, youtube


class Adapter(Protocol):
    platform: str

    def publish(self, content: str, media_urls: list[str] | None = None,
                settings: dict | None = None, account_extra: dict | None = None) -> tuple[bool, str, str]: ...


ADAPTERS: dict[str, Adapter] = {
    "x": twitter,
    "twitter": twitter,
    "instagram": instagram,
    "tiktok": tiktok,
    "youtube": youtube,
    "linkedin": linkedin,
    "facebook": facebook,
    "bluesky": bluesky,
}
