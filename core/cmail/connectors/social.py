from __future__ import annotations

from .base import Observation


PLATFORM_URLS = {
    "x": "https://x.com/i/flow/signup",
    "instagram": "https://www.instagram.com/accounts/emailsignup/",
    "tiktok": "https://www.tiktok.com/signup",
    "youtube": "https://www.youtube.com/",
    "bluesky": "https://bsky.app/",
}


class SocialConnector:
    kind = "social"

    def observe(self, desired: dict) -> Observation:
        platform = str(desired.get("platform", "social")).lower()
        handle = desired.get("handle")
        state = desired.get("state", "unknown")
        required = desired.get("required", True)
        if not required:
            return Observation("READY", f"{platform} is optional", observed={"required": False})
        if handle and state == "connected":
            return Observation("READY", f"{platform} @{handle} recorded as connected",
                               observed={"platform": platform, "handle": handle, "source": "passport"})
        if handle:
            return Observation("UNKNOWN", f"{platform} @{handle} exists in passport but is not confirmed connected",
                               observed={"platform": platform, "handle": handle}, executor="HUMAN",
                               human_title=f"Confirm {platform} @{handle}",
                               human_instructions=f"Open {platform}, confirm the account is accessible, then mark it connected in the passport. Steve does not bypass login verification or CAPTCHA.",
                               human_url=PLATFORM_URLS.get(platform), estimate_seconds=45, priority=55)
        return Observation("MISSING", f"{platform} account missing", executor="HUMAN",
                           human_title=f"Create {platform} account",
                           human_instructions=f"Create the {platform} account using the project's canonical handle/bio/avatar. Verification, CAPTCHA and legal acceptance remain human steps.",
                           human_url=PLATFORM_URLS.get(platform), estimate_seconds=90, priority=60)
