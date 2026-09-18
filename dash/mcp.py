"""Influence MCP: dependency-graph flow as tools. Read-only; this surface can
never spend, send, or mutate. Writes stay on REST behind the decide gate."""
from __future__ import annotations

import os

TOOLS = [
    {"name": "influencer.list", "description": "List influencers with stage + progress",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "influencer.get", "description": "Influencer resources + states",
     "inputSchema": {"type": "object", "properties": {"slug": {"type": "string"}}, "required": ["slug"]}},
    {"name": "queue.list", "description": "Open human tasks",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "graph.describe", "description": "Dependency-graph layers L0-L7 and function names",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "product.list", "description": "Product registry with infra/surface kinds",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "product.get", "description": "One product: intent, path, needs, status, next",
     "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
    {"name": "receipt.get", "description": "Receipt by id with independent verification",
     "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}},
]

GRAPH = [
    {"layer": "L0 law", "functions": ["canonical", "hash", "store.append", "gates.execute",
      "grants.verify", "receipts.transition", "receipts.settle", "actuality",
      "privacy.compose", "journal", "vault.resolve"]},
    {"layer": "L1 observe", "functions": ["domain.verify", "handles.map", "registrar.compare",
      "zone.read", "mailbox.check", "social.read", "inbox.read", "analytics.read", "tee.attest"]},
    {"layer": "L2 acquire", "functions": ["domain.register", "zone.move", "mailbox.create",
      "number.provision", "social.claim", "key.deposit"], "gate": "human"},
    {"layer": "L3 make", "functions": ["draft.write", "set.write", "voice.render", "face.render",
      "take.render", "bundle.seal"]},
    {"layer": "L4 send", "functions": ["post.publish", "video.send", "mail.send",
      "gift.send", "xmr.pay"], "gate": "human+grant"},
    {"layer": "L5 judge", "functions": ["funny.score", "lands.noul", "lineage.choice",
      "intent.choice", "urgency.score", "risk.score", "drift.noul", "delivery.noul",
      "guardrail.noul"], "note": "proposes only, never executes"},
    {"layer": "L6 learn", "functions": ["rsi.reweight", "hloop.predict", "lineage.promote",
      "reputation.derive"], "note": "proposes only, promotion by receipt"},
    {"layer": "L7 endpoints", "functions": ["influencer()", "agent()", "audience()"],
     "note": "identities are resolutions, not primitives"},
]

PRODUCTS = [
    {"name": "setup.social", "kind": "infra", "intent": "Identity provisioning for other products"},
    {"name": "funnylab", "kind": "infra", "intent": "Simulate-only comedy loop, no gates, no moat"},
    {"name": "eval-api", "kind": "infra", "intent": "Typed judges as a metered endpoint"},
    {"name": "trend-radar", "kind": "infra", "intent": "Trends mined into ranked candidates"},
    {"name": "private-studio", "kind": "infra", "intent": "TEE runs plus identity-free setup"},
    {"name": "instant-influencer", "kind": "surface", "intent": "Spawn from scratch"},
    {"name": "influencer-ops", "kind": "surface", "intent": "Manage, post, send, renew"},
    {"name": "influencer-studio", "kind": "surface", "intent": "Content engine on the freaktown bridge"},
    {"name": "freaktown-autopilot", "kind": "surface", "intent": "The self-running show"},
    {"name": "watch-loop", "kind": "surface", "intent": "Audience side that closes autopilot"},
    {"name": "clip-farm", "kind": "surface", "intent": "Sets cut into scored clips"},
    {"name": "roast-line", "kind": "surface", "intent": "Crowd-work as a service"},
    {"name": "roast.pet", "kind": "surface", "intent": "Upload your pet, get roasted"},
    {"name": "party-rooms", "kind": "surface", "intent": "Pogtown rooms, gifts, games, hosted"},
    {"name": "guest-bookings", "kind": "surface", "intent": "Outside agents buy stage time"},
    {"name": "storefront", "kind": "surface", "intent": "Influencer stores plus merch lines"},
]

PRODUCT_DETAILS = {
    # Primitives per product live in products/primitives.json (machine twin
    # of products/PRIMITIVES.md) and are folded into product.get below —
    # one surface, no second registry to drift.
    "setup.social": {"path": "L1 observe -> L2 acquire (all human-gated)",
                     "needs": ["layer 0"], "status": "graph + observe live",
                     "next": "registrar compare, zone apply, mailbox create, number bridges"},
    "funnylab": {"path": "corpus -> set.write -> funny.score / lands Noul -> rsi.reweight",
                 "needs": ["pinned corpus", "frozen eval"], "status": "designed",
                 "next": "frozen eval cut, one lineage, first reweight receipt"},
    "eval-api": {"path": "L5 judges + grants + receipts, capability mint per caller",
                 "needs": ["funnylab pairs", "versioned gates"], "status": "structured-output judges today",
                 "next": "one endpoint, one caller, receipts on"},
    "trend-radar": {"path": "L1 observe -> L5 judges -> queue",
                    "needs": ["one trend source connector"], "status": "designed",
                    "next": "one source connector, one radar lens"},
    "private-studio": {"path": "L0 privacy + tee.attest + pmail subgraph",
                       "needs": ["TEE attest connector", "xmr.pay live"], "status": "types + gates live",
                       "next": "one connector, one lens, one attested turn"},
    "instant-influencer": {"path": "setup.social -> draft.write -> L5 judges",
                           "needs": ["setup.social", "trend-radar"], "status": "graph + dash + receipts live",
                           "next": "remaining L2 connectors"},
    "influencer-ops": {"path": "L2 + L4 + L5, delivery settles on readback",
                       "needs": ["instant-influencer endpoint"], "status": "designed",
                       "next": "publisher + inbox connectors, one ops lens"},
    "influencer-studio": {"path": "L3 + freaktown bundles, digest-pinned both ways",
                          "needs": ["talent", "freaktown stage"], "status": "both sides exist",
                          "next": "one sealed bundle import, one job with receipt"},
    "freaktown-autopilot": {"path": "L3 -> L5 -> L6 over HAHA/CLAP + eval + analytics",
                            "needs": ["funnylab", "studio", "watch-loop"], "status": "loop designed",
                            "next": "reward ingestion, one lineage + eval gate"},
    "watch-loop": {"path": "audience() emitters -> L6",
                   "needs": ["autopilot show", "party-rooms venue"], "status": "designed",
                   "next": "watch lens with clips + reaction buttons"},
    "clip-farm": {"path": "L3 cut -> L5 clip judges -> L4 gated publish",
                  "needs": ["sets", "eval-api"], "status": "designed",
                  "next": "one cutter connector, one clip lens"},
    "roast-line": {"path": "L3 -> L5 roast rubric -> gated send",
                   "needs": ["eval-api", "funnylab"], "status": "designed",
                   "next": "roast rubric as Score criteria"},
    "roast.pet": {"path": "roast-line + image observe + Etsy orders as tasks",
                  "needs": ["setup.social web records", "roast-line"], "status": "pipeline live in etsysignal",
                  "next": "web records, order queue wired, first receipted roast"},
    "party-rooms": {"path": "L7 rooms (pogtown packs as truth) -> events",
                    "needs": ["pogtown adapter"], "status": "packs + runtime live in-repo",
                    "next": "hosted room one, events to run log"},
    "guest-bookings": {"path": "L7 agent links -> rooms -> events, bounded grants",
                       "needs": ["party-rooms", "stage"], "status": "designed",
                       "next": "booking passport, one external guest"},
    "storefront": {"path": "setup.social subdomain -> listings -> orders -> fulfillment -> payout",
                   "needs": ["money-proof gates green"], "status": "designed",
                   "next": "listing kinds, one provider, one test order with receipt"},
}


def _receipt_store_path() -> str:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.getenv("RECEIPT_LOG", os.path.join(root, "dash", "receipts.jsonl"))


def _find_receipt(rid: str):
    import json
    path = _receipt_store_path()
    if not os.path.exists(path):
        return None, None
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            payload = entry.get("payload", entry)
            rc = payload.get("receipt", {})
            if rc.get("id") == rid:
                return rc, payload.get("evidence", [])
    return None, None


def _primitives() -> dict:
    """products/primitives.json, cached. Missing file = empty (dash still serves)."""
    if not hasattr(_primitives, "cache"):
        import json
        try:
            with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                   "products", "primitives.json")) as f:
                _primitives.cache = {p["name"]: p for p in json.load(f)["products"]}  # type: ignore[attr-defined]
        except Exception:
            _primitives.cache = {}  # type: ignore[attr-defined]
    return _primitives.cache  # type: ignore[return-value]


def handle(state: dict, method: str, params: dict) -> dict:
    if method == "tools/list":
        return {"tools": TOOLS}
    if method != "tools/call":
        return {"error": "unknown method"}
    name, args = params.get("name"), params.get("arguments", {})
    if name == "influencer.list":
        out = []
        for i in state["influencers"]:
            ready = sum(1 for r in i["resources"] if r["status"] == "READY")
            out.append({"slug": i["slug"], "name": i["name"], "stage": i["stage"],
                        "ready": ready, "total": len(i["resources"])})
        return {"result": out}
    if name == "influencer.get":
        inf = next((i for i in state["influencers"] if i["slug"] == args.get("slug")), None)
        return {"result": inf} if inf else {"error": "unknown influencer"}
    if name == "queue.list":
        return {"result": state["tasks"]}
    if name == "graph.describe":
        return {"result": GRAPH}
    if name == "product.list":
        return {"result": PRODUCTS}
    if name == "product.get":
        d = PRODUCT_DETAILS.get(args.get("slug", args.get("name", "")))
        base = next((p for p in PRODUCTS if p["name"] == args.get("slug", args.get("name", ""))), None)
        if d is None or base is None:
            return {"error": "unknown product"}
        prim = _primitives().get(args.get("slug", args.get("name", "")), {})
        return {"result": {**base, **d, "primitives": prim}}
    if name == "receipt.get":
        rc, ev = _find_receipt(str(args.get("id", "")))
        if rc is None:
            return {"error": "unknown receipt"}
        try:
            import sys
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from qp.law import use_law
            use_law()
            from acom import receipts as R
            v = R.settle(rc, ev)
            return {"result": {"receipt": rc, "verify": v}}
        except Exception:
            return {"result": {"receipt": rc, "verify": {"ok": None, "reason": "verifier unavailable"}}}
    return {"error": f"unknown tool {name}"}
