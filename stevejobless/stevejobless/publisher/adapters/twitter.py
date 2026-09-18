"""X / Twitter adapter — v2 API via tweepy."""
from __future__ import annotations

import os

platform = "x"


def publish(content: str, media_urls: list[str] | None = None,
            settings: dict | None = None, account_extra: dict | None = None) -> tuple[bool, str, str]:
    extra = account_extra or {}
    api_key = extra.get("api_key") or os.getenv("X_API_KEY", "")
    api_secret = extra.get("api_secret") or os.getenv("X_API_SECRET", "")
    access_token = extra.get("access_token") or os.getenv("X_ACCESS_TOKEN", "")
    access_secret = extra.get("access_secret") or os.getenv("X_ACCESS_TOKEN_SECRET", "")

    if not all([api_key, api_secret, access_token, access_secret]):
        return False, "", "X credentials missing (api_key, api_secret, access_token, access_secret)"

    try:
        import tweepy
    except ImportError:
        return False, "", "tweepy not installed (pip install tweepy)"

    try:
        client = tweepy.Client(
            consumer_key=api_key, consumer_secret=api_secret,
            access_token=access_token, access_token_secret=access_secret,
        )

        media_ids: list[str] = []
        if media_urls:
            api_v1 = tweepy.API(tweepy.OAuth1UserHandler(
                api_key, api_secret, access_token, access_secret,
            ))
            for url in media_urls[:4]:
                m = api_v1.media_upload(filename=url)
                media_ids.append(str(m.media_id))

        kwargs: dict = {"text": content[:280]}
        if media_ids:
            kwargs["media_ids"] = media_ids

        resp = client.create_tweet(**kwargs)
        post_id = str(resp.data["id"])
        return True, post_id, ""
    except Exception as e:
        return False, "", f"x error: {e}"
