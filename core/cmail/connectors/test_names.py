"""Names connector tests. No network in unit tests: empty desired is
MISSING, unreachable checker is UNKNOWN (fail closed, never a verdict)."""
import os

from .names import NamesConnector


def test_empty_desired_is_missing():
    obs = NamesConnector().observe({})
    assert obs.status == "MISSING" and obs.executor == "HUMAN"


def test_unreachable_checker_is_unknown(monkeypatch):
    monkeypatch.setenv("NAMES_CHECKER_URL", "http://127.0.0.1:9")
    import importlib
    import core.cmail.connectors.names as names_mod
    importlib.reload(names_mod)
    try:
        obs = names_mod.NamesConnector().observe({"domain": "example.com"})
        assert obs.status == "UNKNOWN"
    finally:
        monkeypatch.undo()
        importlib.reload(names_mod)


def test_registered_kind():
    assert NamesConnector().kind == "names"
