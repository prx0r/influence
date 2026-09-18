"""Tests for the publisher module."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from stevejobless.db import Base
from stevejobless.publisher.models import PostQueue, SocialAccount
from stevejobless.publisher.adapters import ADAPTERS


def test_all_adapters_registered():
    expected = {"x", "twitter", "instagram", "tiktok", "youtube", "linkedin", "facebook", "bluesky"}
    assert set(ADAPTERS.keys()) == expected


def test_adapter_has_publish_method():
    for name, adapter in ADAPTERS.items():
        assert hasattr(adapter, "publish"), f"{name} missing publish"
        assert hasattr(adapter, "platform"), f"{name} missing platform"


def test_post_queue_model():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as db:
        post = PostQueue(
            business_slug="test-app",
            platform="x",
            content="Hello world!",
            status="draft",
        )
        db.add(post)
        db.commit()
        assert post.id > 0
        assert post.status == "draft"
        assert post.attempts == 0


def test_social_account_model():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as db:
        account = SocialAccount(
            business_slug="test-app",
            platform="x",
            provider_account_id="12345",
            display_name="Test User",
            access_token="tok_test",
        )
        db.add(account)
        db.commit()
        assert account.id > 0
        assert account.platform == "x"


def test_twitter_adapter_missing_credentials():
    from stevejobless.publisher.adapters import twitter
    ok, post_id, error = twitter.publish("test")
    assert ok is False
    assert "missing" in error.lower() or "credential" in error.lower()


def test_instagram_adapter_missing_credentials():
    from stevejobless.publisher.adapters import instagram
    ok, post_id, error = instagram.publish("test", media_urls=["http://example.com/img.jpg"])
    assert ok is False
    assert "missing" in error.lower() or "ig_" in error.lower()


def test_tiktok_adapter_missing_credentials():
    from stevejobless.publisher.adapters import tiktok
    ok, post_id, error = tiktok.publish("test", media_urls=["http://example.com/video.mp4"])
    assert ok is False
    assert "missing" in error.lower() or "token" in error.lower()


def test_youtube_adapter_missing_credentials():
    from stevejobless.publisher.adapters import youtube
    ok, post_id, error = youtube.publish("test", media_urls=["/tmp/video.mp4"])
    assert ok is False
    assert "missing" in error.lower() or "client" in error.lower()


def test_linkedin_adapter_missing_credentials():
    from stevejobless.publisher.adapters import linkedin
    ok, post_id, error = linkedin.publish("test")
    assert ok is False
    assert "missing" in error.lower() or "token" in error.lower()


def test_facebook_adapter_missing_credentials():
    from stevejobless.publisher.adapters import facebook
    ok, post_id, error = facebook.publish("test")
    assert ok is False
    assert "missing" in error.lower() or "page" in error.lower()


def test_bluesky_adapter_missing_credentials():
    from stevejobless.publisher.adapters import bluesky
    ok, post_id, error = bluesky.publish("test")
    assert ok is False
    assert "missing" in error.lower() or "handle" in error.lower()
