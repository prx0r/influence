from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class PostizPublisher:
    """Create, schedule, and manage posts through the Postiz public API.

    Used by SteveJobless autopilot and API endpoints to publish content
    across all connected social channels.
    """

    def __init__(self, base_url: str, api_key: str):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    def _headers(self, content_type: str = "application/json") -> dict[str, str]:
        h = {"Authorization": self._api_key, "Accept": "application/json"}
        if content_type:
            h["Content-Type"] = content_type
        return h

    def _request(self, method: str, path: str, body: dict | None = None) -> dict[str, Any]:
        url = f"{self._base_url}/public/v1{path}"
        data = json.dumps(body).encode() if body else None
        req = Request(url, data=data, headers=self._headers(), method=method)
        with urlopen(req, timeout=30) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}

    # ── Integrations ──────────────────────────────────────────────

    def list_integrations(self, group: str | None = None) -> list[dict[str, Any]]:
        path = "/integrations"
        if group:
            path += f"?group={group}"
        result = self._request("GET", path)
        return result if isinstance(result, list) else []

    def get_integration(self, integration_id: str) -> dict[str, Any] | None:
        integrations = self.list_integrations()
        return next((i for i in integrations if i.get("id") == integration_id), None)

    def find_integration(self, platform: str, group: str | None = None) -> dict[str, Any] | None:
        for i in self.list_integrations(group):
            if i.get("identifier") == platform:
                return i
        return None

    # ── Posts ─────────────────────────────────────────────────────

    def create_post(
        self,
        integration_id: str,
        content: str,
        *,
        post_type: str = "schedule",
        date: str | None = None,
        images: list[dict[str, str]] | None = None,
        settings: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        short_link: bool = False,
        group: str | None = None,
    ) -> dict[str, Any]:
        if post_type == "schedule" and not date:
            now = datetime.now(timezone.utc)
            date = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        post_content: dict[str, Any] = {"content": content, "image": images or []}
        post_item: dict[str, Any] = {
            "integration": {"id": integration_id},
            "value": [post_content],
        }
        if settings:
            post_item["settings"] = settings

        body: dict[str, Any] = {
            "type": post_type,
            "date": date or "",
            "shortLink": short_link,
            "tags": tags or [],
            "posts": [post_item],
        }
        if group:
            body["group"] = group

        return self._request("POST", "/posts", body)

    def post_now(
        self,
        integration_id: str,
        content: str,
        *,
        images: list[dict[str, str]] | None = None,
        settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.create_post(
            integration_id, content,
            post_type="now", images=images, settings=settings,
        )

    def schedule_post(
        self,
        integration_id: str,
        content: str,
        date: str,
        *,
        images: list[dict[str, str]] | None = None,
        settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.create_post(
            integration_id, content,
            post_type="schedule", date=date, images=images, settings=settings,
        )

    def draft_post(
        self,
        integration_id: str,
        content: str,
        *,
        images: list[dict[str, str]] | None = None,
        settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.create_post(
            integration_id, content,
            post_type="draft", images=images, settings=settings,
        )

    def list_posts(
        self,
        start_date: str,
        end_date: str,
        customer: str | None = None,
    ) -> list[dict[str, Any]]:
        path = f"/posts?startDate={start_date}&endDate={end_date}"
        if customer:
            path += f"&customer={customer}"
        result = self._request("GET", path)
        return result.get("posts", []) if isinstance(result, dict) else []

    def delete_post(self, post_id: str) -> dict[str, Any]:
        return self._request("DELETE", f"/posts/{post_id}")

    # ── Uploads ───────────────────────────────────────────────────

    def upload_media(self, file_path: str) -> dict[str, Any]:
        import mimetypes
        boundary = "----SteveJoblessBoundary"
        filename = file_path.rsplit("/", 1)[-1]
        content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"

        with open(file_path, "rb") as f:
            file_data = f.read()

        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode() + file_data + f"\r\n--{boundary}--\r\n".encode()

        url = f"{self._base_url}/public/v1/upload"
        req = Request(url, data=body, method="POST")
        req.add_header("Authorization", self._api_key)
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
        with urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())

    # ── Analytics ─────────────────────────────────────────────────

    def get_integration_analytics(self, integration_id: str, date: str | None = None) -> dict[str, Any]:
        path = f"/analytics/{integration_id}"
        if date:
            path += f"?date={date}"
        return self._request("GET", path)

    def get_post_analytics(self, post_id: str, date: str | None = None) -> dict[str, Any]:
        path = f"/analytics/posts/{post_id}"
        if date:
            path += f"?date={date}"
        return self._request("GET", path)

    # ── Groups ────────────────────────────────────────────────────

    def list_groups(self) -> list[dict[str, Any]]:
        result = self._request("GET", "/groups")
        return result if isinstance(result, list) else []

    # ── Health ────────────────────────────────────────────────────

    def health_check(self) -> bool:
        try:
            self._request("GET", "/is-connected")
            return True
        except (HTTPError, URLError, OSError):
            return False
