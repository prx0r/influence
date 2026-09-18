import os
from pathlib import Path

# Smoke-test import and route availability; DB behavior is covered separately.
def test_app_imports():
    from fastapi.routing import APIRoute
    from stevejobless.main import app
    paths = {r.path for r in app.routes if isinstance(r, APIRoute)}
    assert "/health" in paths
    assert "/api/projects" in paths
    assert "/api/reconcile" in paths
