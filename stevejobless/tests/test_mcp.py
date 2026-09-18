"""Unified read-only MCP tests."""
import os
import tempfile

_fd, _db = tempfile.mkstemp(suffix=".db")
os.close(_fd)
os.environ["STEVE_DB_URL"] = f"sqlite:///{_db}"

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    from stevejobless.main import app

    with TestClient(app) as c:
        yield c


def test_tools_list(client):
    r = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).json()
    names = [t["name"] for t in r["result"]["tools"]]
    assert names == ["job.list", "job.get", "name.check", "name.handles", "biz.status", "email.needs_reply"]


def test_unknown_tool_and_method(client):
    r = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                  "params": {"name": "money.spend", "arguments": {}}}).json()
    assert r["error"]["code"] == -32602
    r2 = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/destroy"}).json()
    assert r2["error"]["code"] == -32601


def test_job_list_empty_ok(client):
    r = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                  "params": {"name": "job.list", "arguments": {"slug": "sparky"}}}).json()
    assert "content" in r["result"]


def test_biz_status(client):
    r = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                  "params": {"name": "biz.status", "arguments": {"slug": "sparky"}}}).json()
    assert "kernel" in r["result"]["content"][0]["text"]
