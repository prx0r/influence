"""Tests for Postiz connector and publisher."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

from stevejobless.connectors.postiz import PostizConnector
from stevejobless.postiz import PostizPublisher


class TestPostizConnector:
    def test_unconfigured_falls_back_to_passport(self):
        conn = PostizConnector()
        result = conn.observe({"platform": "x", "handle": "myhandle"})
        assert result.status == "UNKNOWN"
        assert "Postiz not configured" in result.message

    def test_missing_handle_returns_missing(self):
        conn = PostizConnector()
        result = conn.observe({"platform": "x"})
        assert result.status == "MISSING"

    def test_optional_resource_always_ready(self):
        conn = PostizConnector()
        result = conn.observe({"platform": "x", "required": False})
        assert result.status == "READY"

    def test_unreachable_postiz_returns_error(self):
        conn = PostizConnector(base_url="http://localhost:9999", api_key="test-key")
        result = conn.observe({"platform": "x", "handle": "test"})
        assert result.status == "ERROR"
        assert "unreachable" in result.message.lower()

    @patch("stevejobless.connectors.postiz.urlopen")
    def test_matching_integration_ready(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps([
            {"id": "int-1", "identifier": "x", "name": "Test X", "profile": "testx", "disabled": False, "customer": None}
        ]).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        conn = PostizConnector(base_url="http://localhost:5000", api_key="test-key")
        result = conn.observe({"platform": "x", "handle": "testx"})
        assert result.status == "READY"
        assert result.observed["source"] == "postiz"

    @patch("stevejobless.connectors.postiz.urlopen")
    def test_no_matching_platform_returns_missing(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps([
            {"id": "int-1", "identifier": "linkedin", "name": "Test LinkedIn", "disabled": False}
        ]).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        conn = PostizConnector(base_url="http://localhost:5000", api_key="test-key")
        result = conn.observe({"platform": "x", "handle": "testx"})
        assert result.status == "MISSING"

    @patch("stevejobless.connectors.postiz.urlopen")
    def test_disabled_channel_returns_blocked(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps([
            {"id": "int-1", "identifier": "x", "name": "Test X", "disabled": True}
        ]).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        conn = PostizConnector(base_url="http://localhost:5000", api_key="test-key")
        result = conn.observe({"platform": "x", "handle": "testx"})
        assert result.status == "BLOCKED"


class TestPostizPublisher:
    @patch("stevejobless.postiz.urlopen")
    def test_list_integrations(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps([
            {"id": "int-1", "identifier": "x", "name": "Test X"}
        ]).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        pub = PostizPublisher("http://localhost:5000", "test-key")
        result = pub.list_integrations()
        assert len(result) == 1
        assert result[0]["identifier"] == "x"

    @patch("stevejobless.postiz.urlopen")
    def test_create_post_now(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"id": "post-1"}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        pub = PostizPublisher("http://localhost:5000", "test-key")
        result = pub.post_now("int-1", "Hello world!")
        assert result["id"] == "post-1"

    @patch("stevejobless.postiz.urlopen")
    def test_health_check_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"connected": True}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        pub = PostizPublisher("http://localhost:5000", "test-key")
        assert pub.health_check() is True

    @patch("stevejobless.postiz.urlopen", side_effect=URLError("connection refused"))
    def test_health_check_failure(self, mock_urlopen):
        pub = PostizPublisher("http://localhost:5000", "test-key")
        assert pub.health_check() is False
