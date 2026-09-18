"""Coverage: every product names its primitives; every live gate/connector exists."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dash.mcp import PRODUCTS
from qp.law import use_law

use_law()
from acom import gates as G
from core.cmail.connectors import CONNECTORS

PRIMS = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                    "products", "primitives.json")))["products"]
BY_NAME = {p["name"]: p for p in PRIMS}


def test_every_product_has_primitives():
    for p in PRODUCTS:
        assert p["name"] in BY_NAME, f"no primitives entry for {p['name']}"
        assert BY_NAME[p["name"]]["kind"] == p["kind"], p["name"]


def test_live_gates_exist_in_law():
    for p in PRIMS:
        for g in p["gates_live"]:
            assert g in G.REGISTRY, f"{p['name']}: gate {g} not in law registry"


def test_live_connectors_exist():
    for p in PRIMS:
        for c in p["connectors_live"]:
            assert c in CONNECTORS, f"{p['name']}: connector {c} not registered"


def test_status_honest():
    for p in PRIMS:
        assert p["status"] in ("live", "partial", "designed"), p["name"]
