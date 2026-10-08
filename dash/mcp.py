"""Influence MCP: dependency-graph flow as tools. Read-only; this surface can
never spend, send, or mutate. Writes stay on REST behind the decide gate."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

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
    {"name": "identity.list", "description": "List all identities (businesses/brands)",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "identity.get", "description": "Get identity details with slot statuses",
     "inputSchema": {"type": "object", "properties": {"slug": {"type": "string"}}, "required": ["slug"]}},
    {"name": "identity.create", "description": "Create a new identity with auto-initialized slots",
     "inputSchema": {"type": "object", "properties": {"slug": {"type": "string"}, "name": {"type": "string"}, "category": {"type": "string"}, "niche": {"type": "string"}}, "required": ["slug", "name"]}},
    {"name": "identity.slot", "description": "Update an identity slot (domain, email, phone, socials, website)",
     "inputSchema": {"type": "object", "properties": {"slug": {"type": "string"}, "slot": {"type": "string"}, "fields": {"type": "object"}, "status": {"type": "string"}}, "required": ["slug", "slot"]}},
    {"name": "brand.voice", "description": "Inhabit pack for a brand: voice, style_lock, handles, bio, design rules, gates (bgraph spine + commerce truth)",
     "inputSchema": {"type": "object", "properties": {"slug": {"type": "string"}}, "required": ["slug"]}},
    {"name": "brand.graphs", "description": "Company graphs an entity can see: bgraph export, dash project, site/companygraph, primitives (entity is the selector)",
     "inputSchema": {"type": "object", "properties": {"slug": {"type": "string"}}, "required": ["slug"]}},
    {"name": "content.signals", "description": "Get top signals from a data garden (powpowpow, ukgraph, etc.)",
     "inputSchema": {"type": "object", "properties": {"garden": {"type": "string"}, "limit": {"type": "integer"}}}},
    {"name": "content.build", "description": "Build content from a signal (hook + claim + beats)",
     "inputSchema": {"type": "object", "properties": {"signal": {"type": "object"}, "template": {"type": "string"}}}},
    {"name": "content.narrate", "description": "Generate narration audio from content",
     "inputSchema": {"type": "object", "properties": {"content_id": {"type": "string"}}}},
    {"name": "content.status", "description": "Check content pipeline status",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "studio.lora1", "description": "Locked sleep B&W draw recipe (knobs+rules)",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "studio.art", "description": "List sleep studio art gallery",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "studio.generate", "description": "Generate FLUX art (pencil/paper/chalk)",
     "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string"}, "style": {"type": "string"}, "model": {"type": "string"}}, "required": ["prompt"]}},
    {"name": "studio.render", "description": "Render art to 30s draw clip (async, returns jid)",
     "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}, "knobs": {"type": "object"}}, "required": ["name"]}},
    {"name": "studio.job", "description": "Poll a studio render job",
     "inputSchema": {"type": "object", "properties": {"jid": {"type": "string"}}, "required": ["jid"]}},
    {"name": "studio.publish", "description": "Publish a finished render to the test channel",
     "inputSchema": {"type": "object", "properties": {"jid": {"type": "string"}, "title": {"type": "string"}}, "required": ["jid", "title"]}},
    {"name": "studio.narrate", "description": "Voice iteration: edge-tts MP3 (aria/guy/ana/christopher)",
     "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}, "voice": {"type": "string"}}, "required": ["text"]}},
    {"name": "phone.status", "description": "Brand phone status (number, inbound counts) from phone.agentcom.org",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "phone.sms", "description": "Inbound SMS from brand phone inbox (free read)",
     "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer"}, "slug": {"type": "string"}}}},
    {"name": "phone.calls", "description": "Call events from brand phone inbox (free read)",
     "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer"}, "slug": {"type": "string"}}}},
    {"name": "phone.callbacks", "description": "Queued human callbacks (return SMS/call)",
     "inputSchema": {"type": "object", "properties": {"slug": {"type": "string"}}}},
    {"name": "phone.send", "description": "Send SMS from brand number — HUMAN GATED, never auto",
     "inputSchema": {"type": "object", "properties": {"to": {"type": "string"}, "text": {"type": "string"}, "slug": {"type": "string"}, "confirm": {"type": "boolean"}}, "required": ["to", "text"]}},
    {"name": "social.onboarding", "description": "Brand-agnostic social claim kit from data/social_onboarding.v1.json (steps, bios, pin posts)",
     "inputSchema": {"type": "object", "properties": {"slug": {"type": "string"}, "handle": {"type": "string"}, "domain": {"type": "string"}, "platforms": {"type": "array", "items": {"type": "string"}}}}},
    {"name": "social.platforms", "description": "List onboarding platforms from the social registry",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "email.inbox", "description": "Brand inbox from cmail worker (filter by mailbox e.g. hello@oddhobb.com)",
     "inputSchema": {"type": "object", "properties": {"mailbox": {"type": "string"}, "limit": {"type": "integer"}, "needs_reply": {"type": "boolean"}}}},
    {"name": "email.stats", "description": "cmail inbox counters (needs_me / total)",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "email.read", "description": "Read one email by message_id (meta + raw body from cmail)",
     "inputSchema": {"type": "object", "properties": {"message_id": {"type": "string"}}, "required": ["message_id"]}},
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
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from qp.law import use_law
            use_law()
            from acom import receipts as R
            v = R.settle(rc, ev)
            return {"result": {"receipt": rc, "verify": v}}
        except Exception:
            return {"result": {"receipt": rc, "verify": {"ok": None, "reason": "verifier unavailable"}}}
    if name == "identity.list":
        from core.identity import Identity
        ident = Identity(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "identities"))
        all_ids = ident.list_all()
        return {"result": [{"slug": i["slug"], "name": i["name"], "category": i.get("category", ""),
                            "ready": sum(1 for s in i["slots"].values() if s["status"] == "ready"),
                            "total": len(i["slots"])} for i in all_ids]}
    if name == "identity.get":
        from core.identity import Identity
        ident = Identity(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "identities"))
        result = ident.get_status(args.get("slug", ""))
        return {"result": result} if "error" not in result else {"error": result["error"]}
    if name == "identity.create":
        from core.identity import Identity
        ident = Identity(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "identities"))
        result = ident.create(args["slug"], args["name"], args.get("category", ""), args.get("niche", ""))
        return {"result": result}
    if name == "identity.slot":
        from core.identity import Identity
        ident = Identity(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "identities"))
        try:
            ident.update_slot(args["slug"], args["slot"], args.get("fields", {}), args.get("status"))
            return {"result": ident.get_status(args["slug"])}
        except Exception as e:
            return {"error": str(e)[:200]}
    if name == "brand.graphs":
        slug = str(args.get("slug", "")).strip().lower()
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        graphs: dict = {"slug": slug}
        bp = os.path.join(root, "bgraph", "exports", f"{slug}.json")
        graphs["bgraph_export"] = bp if os.path.exists(bp) else None
        graphs["bgraph_registry"] = os.path.join(root, "bgraph", "registry", "brands", f"{slug}.json") if os.path.exists(
            os.path.join(root, "bgraph", "registry", "brands", f"{slug}.json")) else None
        sp = os.path.join(root, "oddhobbies", "stores", slug, "store.json")
        graphs["commerce_pack"] = sp if os.path.exists(sp) else None
        graphs["dash_project"] = slug
        graphs["site_companygraph"] = f"https://{slug}.com/api/companygraph" if slug in ("oddhobb",) else None
        graphs["primitives"] = "influence/products/primitives.json"
        graphs["note"] = "entity is the selector: every graph keys off slug/store_id"
        return {"result": graphs}
    if name == "brand.voice":
        slug = str(args.get("slug", "")).strip().lower()
        if slug == "humanvoiced":
            return {"result": {
                "slug": "humanvoiced", "display_name": "HumanVoiced",
                "domain": "humanvoiced.com", "email": "hello@humanvoiced.com",
                "handles": {"primary": "@humanvoiced"},
                "voice": "Clear, direct marketplace operator. Real voices, on demand.",
                "style_lock": {"background": "clean product UI",
                               "avoid": ["synthetic-voice claims", "unverified stats"]},
                "branches": [], "publish_gate": "human_confirm",
                "commerce": {"thesis": "Human voice marketplace: narration, series, dubbing."},
                "instructions": "Inhabit HumanVoiced: marketplace operator voice. Drafts only — publish stays human_confirm."}}
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        try:
            with open(os.path.join(root, "bgraph", "registry", "brands", f"{slug}.json")) as f:
                b = json.load(f)
        except Exception:
            return {"error": f"unknown brand {slug}"}
        ident = b.get("identity", {}) or {}
        branches = []
        for br in b.get("branches", []):
            acc = br.get("account") or {}
            branches.append({"platform": br.get("platform"), "handle": acc.get("handle"),
                             "status": acc.get("status"), "content_types": br.get("content_types")})
        pack: dict = {"slug": slug,
            "display_name": ident.get("display_name"), "domain": ident.get("domain"),
            "email": ident.get("email"),
            "handles": ident.get("confirmed_socials") or {"primary": ident.get("handle_primary")},
            "voice": ident.get("voice"), "style_lock": ident.get("style_lock"),
            "branches": branches, "publish_gate": "human_confirm"}
        try:
            with open(os.path.join(root, "oddhobbies", "stores", slug, "store.json")) as f:
                s = json.load(f)
            pack["commerce"] = {"store_name": s.get("store_name"), "brand_line": s.get("brand_line"),
                                "thesis": s.get("thesis"), "style_lock": s.get("style_lock"),
                                "sections": s.get("sections")}
        except Exception:
            pack["commerce"] = {}
        pack["instructions"] = (f"Inhabit {pack['display_name']}: write in voice, honor style_lock avoid-list, "
                                f"link {pack['domain']}. Drafts only — publish stays human_confirm.")
        return {"result": pack}
    if name == "content.signals":
        import subprocess
        content_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "content")
        garden = args.get("garden", "powpowpow")
        limit = args.get("limit", 5)
        try:
            r = subprocess.run(["python3", os.path.join(content_dir, "mcp_server.py"),
                               "signals_top", json.dumps({"garden": garden, "limit": limit})],
                              capture_output=True, text=True, timeout=30, cwd=content_dir)
            return {"result": json.loads(r.stdout)} if r.stdout else {"error": r.stderr[:200]}
        except Exception as e:
            return {"error": str(e)[:200]}
    if name == "content.build":
        import subprocess
        content_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "content")
        try:
            r = subprocess.run(["python3", os.path.join(content_dir, "mcp_server.py"),
                               "build_content", json.dumps({"signal": args.get("signal"), "template": args.get("template", "anomaly")})],
                              capture_output=True, text=True, timeout=30, cwd=content_dir)
            return {"result": json.loads(r.stdout)} if r.stdout else {"error": r.stderr[:200]}
        except Exception as e:
            return {"error": str(e)[:200]}
    if name == "content.narrate":
        import subprocess
        content_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "content")
        try:
            r = subprocess.run(["python3", os.path.join(content_dir, "mcp_server.py"),
                               "render_narration", json.dumps({"content_id": args.get("content_id")})],
                              capture_output=True, text=True, timeout=60, cwd=content_dir)
            return {"result": json.loads(r.stdout)} if r.stdout else {"error": r.stderr[:200]}
        except Exception as e:
            return {"error": str(e)[:200]}
    if name == "content.status":
        import subprocess
        content_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "content")
        try:
            r = subprocess.run(["python3", os.path.join(content_dir, "mcp_server.py"),
                               "content_status", "{}"],
                              capture_output=True, text=True, timeout=15, cwd=content_dir)
            return {"result": json.loads(r.stdout)} if r.stdout else {"error": r.stderr[:200]}
        except Exception as e:
            return {"error": str(e)[:200]}
    if name == "studio.lora1":
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
        import sleep_studio as _st
        return {"result": _st.lora1()}
    if name == "studio.art":
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
        import sleep_studio as _st
        return {"result": _st.list_art()}
    if name == "studio.generate":
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
        import sleep_studio as _st
        try:
            return {"result": _st.generate(str(args.get("prompt", "")),
                                           str(args.get("style", "pencil") or "pencil"),
                                           str(args.get("model", "flux") or "flux"))}
        except Exception as e:
            return {"error": str(e)[:300]}
    if name == "studio.render":
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
        import sleep_studio as _st
        try:
            knobs = dict(args.get("knobs", {}) or {})
            if "dur" in knobs:
                knobs["dur"] = int(knobs["dur"])
            return {"result": {"jid": _st.start_render(str(args.get("name", "")), knobs)}}
        except Exception as e:
            return {"error": str(e)[:300]}
    if name == "studio.job":
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
        import sleep_studio as _st
        return {"result": _st.job_status(str(args.get("jid", "")))}
    if name == "studio.publish":
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
        import sleep_studio as _st
        job = _st.JOBS.get(str(args.get("jid", "")))
        if not job or job.get("status") != "done":
            return {"error": "render not done"}
        try:
            return {"result": _st.publish(job["mp4path"], str(args.get("title", "sleep-test")),
                                          {"name": job.get("name"), "knobs": job.get("knobs")})}
        except Exception as e:
            return {"error": str(e)[:300]}
    if name == "studio.narrate":
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
        import sleep_studio as _st
        try:
            return {"result": _st.narrate(str(args.get("text", "")),
                                          str(args.get("voice", "aria") or "aria"))}
        except Exception as e:
            return {"error": str(e)[:300]}
    if name == "email.read":
        import urllib.request as _urlreq
        base = os.environ.get("CMAIL_URL", "https://cmail.tradesprior.workers.dev").rstrip("/")
        mid = str(args.get("message_id") or "")
        if not mid:
            return {"error": "message_id required"}
        try:
            body = json.dumps({"tool": "email.read", "args": {"message_id": mid}, "actor": "owner"}).encode()
            req = _urlreq.Request(
                base + "/mcp",
                data=body,
                headers={"Content-Type": "application/json", "User-Agent": "influence-dash/0.5"},
                method="POST",
            )
            with _urlreq.urlopen(req, timeout=15) as resp:
                return {"result": json.loads(resp.read() or b"{}")}
        except Exception as e:
            return {"error": str(e)[:200]}
    if name == "email.stats":
        import urllib.request as _urlreq
        base = os.environ.get("CMAIL_URL", "https://cmail.tradesprior.workers.dev").rstrip("/")
        try:
            req = _urlreq.Request(base + "/api/stats", headers={"User-Agent": "influence-dash/0.4"})
            with _urlreq.urlopen(req, timeout=12) as resp:
                return {"result": json.loads(resp.read() or b"{}")}
        except Exception as e:
            return {"error": str(e)[:200]}
    if name == "email.inbox":
        import urllib.request as _urlreq
        base = os.environ.get("CMAIL_URL", "https://cmail.tradesprior.workers.dev").rstrip("/")
        mailbox = str(args.get("mailbox") or "")
        limit = min(int(args.get("limit") or 20), 50)
        needs = bool(args.get("needs_reply"))
        try:
            if mailbox:
                # MCP path filters by mailbox
                req = _urlreq.Request(
                    base + "/mcp",
                    data=json.dumps({"tool": "email.inbox", "args": {"mailbox": mailbox}, "actor": "owner"}).encode(),
                    headers={"Content-Type": "application/json", "User-Agent": "influence-dash/0.4"},
                    method="POST",
                )
                with _urlreq.urlopen(req, timeout=15) as resp:
                    body = json.loads(resp.read() or b"{}")
                msgs = body.get("messages") or []
            else:
                path = "/api/inbox?needs_reply=1" if needs else "/api/inbox"
                req = _urlreq.Request(base + path, headers={"User-Agent": "influence-dash/0.4"})
                with _urlreq.urlopen(req, timeout=15) as resp:
                    msgs = json.loads(resp.read() or b"[]")
            return {"result": msgs[:limit]}
        except Exception as e:
            return {"error": str(e)[:200]}
    if name == "social.platforms":
        from core.cmail.social_onboarding import list_platforms
        return {"result": list_platforms()}
    if name == "social.onboarding":
        from core.cmail.social_onboarding import format_onboarding_reply, render_brand_onboarding
        slug = str(args.get("slug") or "")
        handle = str(args.get("handle") or "")
        domain = str(args.get("domain") or "")
        brand: dict = {}
        if slug:
            inf = next((i for i in state.get("influencers", []) if i["slug"] == slug), None)
            if not inf:
                return {"error": f"unknown influencer {slug}"}
            handle = handle or (inf.get("handle") or inf.get("slug", "")).replace("@", "").replace("-", "")
            domain = domain or inf.get("domain") or ""
            # Pull desired passport fields when present
            for r in inf.get("resources", []):
                d = r.get("desired") or {}
                if r.get("key") == "domain" and d.get("domain"):
                    domain = domain or d["domain"]
                kit = r.get("kit") or d.get("kit") or {}
                if kit.get("phone") and not brand.get("phone"):
                    brand["phone"] = kit["phone"]
                if kit.get("email") and not brand.get("email"):
                    brand["email"] = kit["email"]
                if kit.get("website") and not brand.get("website"):
                    brand["website"] = kit["website"]
            brand["display_name"] = inf.get("name") or handle.title()
            if not domain and "." in str(inf.get("slug", "")):
                domain = str(inf["slug"])
        if not handle:
            return {"error": "slug or handle required"}
        if not domain:
            domain = args.get("domain") or f"{handle.lower()}.com"
        platforms = args.get("platforms")
        try:
            on = render_brand_onboarding(handle, domain, platforms=platforms, brand=brand)
        except Exception as e:
            return {"error": str(e)[:200]}
        return {"result": {"onboarding": on, "text": format_onboarding_reply(on)}}
    if name in ("phone.status", "phone.sms", "phone.calls", "phone.callbacks", "phone.send"):
        import urllib.error
        import urllib.request as _urlreq

        # Prefer public agentcom edge; fall back to workers.dev if tunnel cold.
        base = os.environ.get("PHONE_WORKER_URL", "").rstrip("/")
        candidates = [base] if base else []
        candidates += [
            "https://phone.agentcom.org",
            "https://oddhobb-phone.tradesprior.workers.dev",
            "http://127.0.0.1:8794",
        ]
        auth_file = os.environ.get("PHONE_AUTH_FILE", os.path.expanduser("~/stevejobless/.phone_auth"))
        auth = ""
        try:
            auth = Path(auth_file).read_text().strip() if Path(auth_file).exists() else ""
        except Exception:
            auth = ""
        if not auth:
            try:
                import subprocess
                auth = subprocess.run(
                    ["agent-vault", "vault", "credential", "get", "ODDHOBB_PHONE_AUTH", "--vault", "oracle"],
                    capture_output=True, text=True, timeout=10,
                ).stdout.strip()
            except Exception:
                auth = ""
        headers = {"User-Agent": "influence-dash/0.4"}
        if auth:
            headers["Authorization"] = f"Bearer {auth}"

        def _get(path):
            last = None
            for base_i in candidates:
                if not base_i:
                    continue
                try:
                    req = _urlreq.Request(base_i + path, headers=headers)
                    with _urlreq.urlopen(req, timeout=12) as resp:
                        return json.loads(resp.read() or b"{}")
                except Exception as e:
                    last = e
                    continue
            raise last or RuntimeError("no phone inbox reachable")

        try:
            if name == "phone.status":
                return {"result": _get("/v1/status")}
            if name == "phone.sms":
                limit = min(int(args.get("limit") or 30), 100)
                data = _get("/v1/inbox?kind=sms")
                events = data.get("events") or []
                return {"result": events[:limit]}
            if name == "phone.calls":
                limit = min(int(args.get("limit") or 30), 100)
                data = _get("/v1/inbox?kind=call")
                events = data.get("events") or []
                return {"result": events[:limit]}
            if name == "phone.callbacks":
                data = _get("/v1/callbacks")
                return {"result": data.get("callbacks") or []}
            if name == "phone.send":
                if args.get("confirm") is not True:
                    return {"error": "phone.send blocked — pass confirm:true after human approval"}
                return {"error": "outbound send not enabled in influence dash — use owner phone"}
        except Exception as e:
            return {"error": str(e)[:250]}
    return {"error": f"unknown tool {name}"}
