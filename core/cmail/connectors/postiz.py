from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .base import Observation

GUIDES_DIR = Path(__file__).resolve().parent.parent.parent / "docs" / "platform-guides"

PLATFORM_GUIDES = {
    "x": ("X (Twitter)", "x-twitter.md", [
        "1. Go to https://developer.x.com/en/portal/dashboard",
        "2. Create project + app (name it after your startup)",
        "3. Set permissions to Read+Write BEFORE generating tokens",
        "4. Set app type to Automated App or Bot",
        "5. Add callback URI: {postiz_url}/integrations/social/x",
        "6. Generate all 4 keys/tokens and copy them",
        "7. Add API credits ($7/month minimum) — free tier is read-only",
        "8. Set X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET in Postiz .env",
        "9. Restart Postiz → Add Channel → X → Authorize",
    ]),
    "linkedin": ("LinkedIn", "x-twitter.md", [
        "1. Go to https://www.linkedin.com/developers/apps",
        "2. Create an app",
        "3. Add OAuth 2.0 redirect: {postiz_url}/integrations/social/linkedin",
        "4. Request scopes: r_liteprofile, r_emailaddress, w_member_social",
        "5. Copy Client ID and Client Secret to Postiz .env",
        "6. Restart Postiz → Add Channel → LinkedIn → Authorize",
    ]),
    "facebook": ("Facebook Pages", "meta-facebook-instagram.md", [
        "1. Go to https://developers.facebook.com/apps/create",
        "2. Create Business app",
        "3. Add Facebook Login product",
        "4. Set redirect URI: {postiz_url}/integrations/social/facebook",
        "5. Fill in App Domains, Privacy Policy URL, Category",
        "6. Request permissions: pages_show_list, pages_manage_posts, pages_read_engagement, business_management",
        "7. Submit for App Review with screencasts",
        "8. Set App Mode to Live",
        "9. Copy FACEBOOK_APP_ID and FACEBOOK_APP_SECRET to Postiz .env",
        "10. Restart Postiz → Add Channel → Facebook → Authorize",
    ]),
    "instagram": ("Instagram", "meta-facebook-instagram.md", [
        "1. Requires Business or Creator IG account linked to FB Page",
        "2. Switch IG to Professional Account: Settings → Account → Switch to Professional",
        "3. Go to https://developers.facebook.com → your app → Add Product → Instagram",
        "4. Set redirect URI: {postiz_url}/integrations/social/instagram",
        "5. Request: instagram_basic, instagram_content_publish, instagram_manage_comments",
        "6. Add IG Tester in App Roles (or submit for App Review)",
        "7. Accept tester invitation in IG Settings → Apps and Websites",
        "8. Copy FACEBOOK_APP_ID and FACEBOOK_APP_SECRET to Postiz .env",
        "9. Restart Postiz → Add Channel → Instagram → Authorize",
    ]),
    "instagram-standalone": ("Instagram (Standalone)", "meta-facebook-instagram.md", [
        "1. Requires Professional IG account (Business or Creator)",
        "2. Go to https://developers.facebook.com → Create App → Instagram",
        "3. Set redirect URI: {postiz_url}/integrations/social/instagram-standalone",
        "4. Copy INSTAGRAM_APP_ID and INSTAGRAM_APP_SECRET to Postiz .env",
        "5. Restart Postiz → Add Channel → Instagram (Standalone) → Authorize",
    ]),
    "tiktok": ("TikTok", "tiktok.md", [
        "1. Go to https://developers.tiktok.com/apps",
        "2. Create app → Add products: Login Kit + Content Posting API",
        "3. Set redirect URI: {postiz_url}/integrations/social/tiktok",
        "4. Verify your website URLs (download file, upload to domain root)",
        "5. Request scopes: user.info.basic, video.publish, video.list",
        "6. Submit for review with demo video (1-7 days wait)",
        "7. Copy TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET to Postiz .env",
        "8. Restart Postiz → Add Channel → TikTok → Authorize",
    ]),
    "youtube": ("YouTube", "youtube.md", [
        "1. Go to https://console.cloud.google.com",
        "2. Create project → Enable YouTube Data API v3",
        "3. Configure OAuth consent screen (External, add scopes)",
        "4. Create OAuth credentials (Web application)",
        "5. Add redirect URI: {postiz_url}/integrations/social/youtube",
        "6. PUBLISH the OAuth app (tokens expire in 7 days if Testing)",
        "7. Copy YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET to Postiz .env",
        "8. Restart Postiz → Add Channel → YouTube → Authorize",
    ]),
    "reddit": ("Reddit", None, [
        "1. Go to https://www.reddit.com/prefs/apps",
        "2. Click Create App → select Web App",
        "3. Set redirect URI: {postiz_url}/integrations/social/reddit",
        "4. Copy Client ID and Client Secret to Postiz .env",
        "5. Restart Postiz → Add Channel → Reddit → Authorize",
    ]),
    "bluesky": ("Bluesky", None, [
        "1. No developer app needed",
        "2. Just enter your Bluesky handle and app password in Postiz",
        "3. Restart Postiz → Add Channel → Bluesky → Authorize",
    ]),
    "mastodon": ("Mastodon", None, [
        "1. No developer app needed for most instances",
        "2. Just enter your instance URL and authorize in Postiz",
        "3. Restart Postiz → Add Channel → Mastodon → Authorize",
    ]),
    "threads": ("Threads", None, [
        "1. Go to https://developers.facebook.com",
        "2. Create app → Add Threads product",
        "3. Set redirect URI: {postiz_url}/integrations/social/threads",
        "4. Copy THREADS_APP_ID and THREADS_APP_SECRET to Postiz .env",
        "5. Restart Postiz → Add Channel → Threads → Authorize",
    ]),
    "discord": ("Discord", None, [
        "1. Go to https://discord.com/developers/applications",
        "2. Create application → Bot → Copy token",
        "3. Set redirect URI: {postiz_url}/integrations/social/discord",
        "4. Copy DISCORD_CLIENT_ID and DISCORD_CLIENT_SECRET to Postiz .env",
        "5. Restart Postiz → Add Channel → Discord → Authorize",
    ]),
    "slack": ("Slack", None, [
        "1. Go to https://api.slack.com/apps",
        "2. Create New App → From scratch",
        "3. Add OAuth & Permissions → set redirect URI",
        "4. Add scopes: chat:write, channels:read, etc.",
        "5. Copy SLACK_ID and SLACK_SECRET to Postiz .env",
        "6. Restart Postiz → Add Channel → Slack → Authorize",
    ]),
}


class PostizConnector:
    """Verifies social accounts are connected via a self-hosted Postiz instance.

    Reads integrations from the Postiz public API and compares against the
    passport's desired state. Falls back to passport-only mode when Postiz
    is unreachable or unconfigured.
    """

    kind = "postiz_social"

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self._base_url = (base_url or "").rstrip("/")
        self._api_key = api_key or ""

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": self._api_key,
            "Accept": "application/json",
        }

    def _get(self, path: str) -> dict[str, Any] | list[Any] | None:
        if not self._base_url or not self._api_key:
            return None
        url = f"{self._base_url}/public/v1{path}"
        req = Request(url, headers=self._headers(), method="GET")
        try:
            with urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except (HTTPError, URLError, OSError, json.JSONDecodeError):
            return None

    def _list_integrations(self) -> list[dict[str, Any]]:
        data = self._get("/integrations")
        if data is None or not isinstance(data, list):
            return []
        return data

    def _guide_steps(self, platform: str, postiz_url: str) -> list[str] | None:
        info = PLATFORM_GUIDES.get(platform)
        if not info:
            return None
        name, _file, steps = info
        return [s.format(postiz_url=postiz_url or "{postiz_url}") for s in steps]

    def observe(self, desired: dict[str, Any]) -> Observation:
        platform = str(desired.get("platform", "social")).lower()
        handle = desired.get("handle")
        required = desired.get("required", True)
        group = desired.get("postiz_group")

        if not required:
            return Observation("READY", f"{platform} is optional", observed={"required": False})

        integrations = self._list_integrations()
        if not integrations and self._base_url and self._api_key:
            return Observation(
                "ERROR",
                f"Postiz API unreachable at {self._base_url}",
                observed={"postiz_url": self._base_url},
                executor="HUMAN",
                human_title="Check Postiz instance",
                human_instructions=f"Postiz at {self._base_url} is not responding. Verify it is running and the API key is valid.",
                human_url=self._base_url,
                estimate_seconds=120,
                priority=80,
            )

        if not integrations:
            return self._fallback_passport(platform, handle)

        matched = [
            i for i in integrations
            if i.get("identifier") == platform
            and (not group or (i.get("customer") or {}).get("id") == group)
        ]

        if not matched:
            guide = self._guide_steps(platform, self._base_url)
            guide_text = "\n".join(guide) if guide else "No setup guide available."
            return Observation(
                "MISSING",
                f"No {platform} channel connected in Postiz",
                observed={"platform": platform, "integrations_count": len(integrations)},
                executor="HUMAN",
                human_title=f"Connect {platform} in Postiz",
                human_instructions=(
                    f"Set up {platform} in Postiz:\n\n"
                    f"{guide_text}"
                ),
                human_url=f"{self._base_url}" if self._base_url else None,
                estimate_seconds=120,
                priority=70,
            )

        ch = matched[0]
        if ch.get("disabled"):
            return Observation(
                "BLOCKED",
                f"{platform} channel is disabled in Postiz",
                observed={"platform": platform, "integration_id": ch.get("id")},
                executor="HUMAN",
                human_title=f"Re-enable {platform} in Postiz",
                human_instructions=f"Channel {ch.get('name', platform)} is disabled. Re-enable it in Postiz settings.",
                human_url=self._base_url,
                estimate_seconds=60,
                priority=65,
            )

        return Observation(
            "READY",
            f"{platform} connected via Postiz as @{ch.get('profile', '?')}",
            observed={
                "platform": platform,
                "integration_id": ch.get("id"),
                "profile": ch.get("profile"),
                "name": ch.get("name"),
                "source": "postiz",
            },
        )

    def _fallback_passport(self, platform: str, handle: str | None) -> Observation:
        guide = self._guide_steps(platform, self._base_url)
        guide_text = "\n".join(guide) if guide else ""
        if handle:
            return Observation(
                "UNKNOWN",
                f"{platform} @{handle} in passport but Postiz not configured for live check",
                observed={"platform": platform, "handle": handle},
                executor="HUMAN",
                human_title=f"Confirm {platform} @{handle}",
                human_instructions=(
                    f"Postiz is not configured. Manually verify this account is active.\n\n"
                    f"{guide_text}" if guide_text else "Postiz is not configured. Manually verify this account is active."
                ),
                estimate_seconds=45,
                priority=55,
            )
        return Observation(
            "MISSING",
            f"{platform} account missing",
            executor="HUMAN",
            human_title=f"Create {platform} account",
            human_instructions=(
                f"Create the {platform} account:\n\n{guide_text}"
                if guide_text else
                f"Create the {platform} account using the project's canonical handle."
            ),
            estimate_seconds=90,
            priority=60,
        )
