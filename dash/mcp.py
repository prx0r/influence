"""Influence MCP: dependency-graph flow as tools. Read-only by default; the only
writes are draft rows (release.create) and the grant-gated image/audio tools
(images.generate/images.upload, audio.speak/audio.generate — fail closed
without a verified grant + human approval). This surface can never spend,
send, or mutate otherwise. Writes stay on REST behind the decide gate."""
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
    {"name": "brand.delegate", "description": "Hand a task to one entity's subagent (scoped voice, graphs, tools). Global orchestrator fans out per slug; replies stay brand-separated",
     "inputSchema": {"type": "object", "properties": {"slug": {"type": "string"}, "task": {"type": "string"}}, "required": ["slug", "task"]}},
    {"name": "content.signals", "description": "Get top signals from a data garden (powpowpow, ukgraph, etc.)",
     "inputSchema": {"type": "object", "properties": {"garden": {"type": "string"}, "limit": {"type": "integer"}}}},
    {"name": "content.build", "description": "Build content from a signal (hook + claim + beats)",
     "inputSchema": {"type": "object", "properties": {"signal": {"type": "object"}, "template": {"type": "string"}}}},
    {"name": "content.narrate", "description": "Generate narration audio from content",
     "inputSchema": {"type": "object", "properties": {"content_id": {"type": "string"}}}},
    {"name": "content.status", "description": "Check content pipeline status",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "pack.list", "description": "List product packs with validation gaps (read-only)",
     "inputSchema": {"type": "object", "properties": {"store": {"type": "string"}}, "required": []}},
    {"name": "pack.compile", "description": "Dry-run compile one pack (read-only, zero DB writes, never pushes)",
     "inputSchema": {"type": "object", "properties": {"sku": {"type": "string"}, "brand": {"type": "string"}, "channel": {"type": "string"}}, "required": ["sku"]}},
    {"name": "release.create", "description": "Draft ChannelRelease + ReviewBundle + approval task (writes draft rows, never publishes)",
     "inputSchema": {"type": "object", "properties": {"sku": {"type": "string"}, "brand": {"type": "string"}, "channel": {"type": "string"}, "campaign": {"type": "string"}}, "required": ["sku"]}},
    {"name": "task.status", "description": "Poll effect approval task state + payload hash + receipt (read-only)",
     "inputSchema": {"type": "object", "properties": {"task_id": {"type": "integer"}}, "required": ["task_id"]}},
    {"name": "campaign.list", "description": "List campaigns with item counts (read-only)",
     "inputSchema": {"type": "object", "properties": {"brand": {"type": "string"}}, "required": []}},
    {"name": "etsy.listing", "description": "Preview 'add this product to Etsy': template + payload + images + coherence (read-only, never pushes)",
     "inputSchema": {"type": "object", "properties": {"store": {"type": "string"}, "sku": {"type": "string"}}, "required": ["sku"]}},
    {"name": "actions.list", "description": "Audited action ledger with costs (read-only)",
     "inputSchema": {"type": "object", "properties": {"channel": {"type": "string"}, "campaign": {"type": "string"}, "status": {"type": "string"}, "limit": {"type": "integer"}}, "required": []}},
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
    {"name": "images.plan", "description": "Etsy 5+1 image plan for a SKU: formulas + prompts preview + checklist (read-only, never generates)",
     "inputSchema": {"type": "object", "properties": {"store": {"type": "string"}, "sku": {"type": "string"}, "provider": {"type": "string"}}, "required": ["sku"]}},
    {"name": "images.generate", "description": "Generate slot images (dry-run preview by default; live needs approved grant, Cloudflare free)",
     "inputSchema": {"type": "object", "properties": {"store": {"type": "string"}, "sku": {"type": "string"}, "slots": {"type": "array", "items": {"type": "integer"}}, "provider": {"type": "string"}, "live": {"type": "boolean"}, "grant": {"type": "object"}}, "required": ["sku"]}},
    {"name": "images.upload", "description": "Upload images to Etsy ranks 1-5 (dry-run plan by default; live needs approved grant, human-gated)",
     "inputSchema": {"type": "object", "properties": {"store": {"type": "string"}, "sku": {"type": "string"}, "items": {"type": "array", "items": {"type": "object"}}, "live": {"type": "boolean"}, "grant": {"type": "object"}, "campaign": {"type": "string"}}, "required": ["sku"]}},
    {"name": "audio.voices", "description": "Voice casting search (free read: public/team voices, samples, popularity)",
     "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "language": {"type": "string"}, "self": {"type": "boolean"}, "page_size": {"type": "integer"}}}},
    {"name": "audio.voice", "description": "One voice by ID: title, tags, sample URL, uses, likes (free read — ALWAYS use this for a known voice_id, search never finds IDs)",
     "inputSchema": {"type": "object", "properties": {"voice_id": {"type": "string"}}, "required": ["voice_id"]}},
    {"name": "audio.balance", "description": "Fish package credit balance + plan + TTS budget (free read)",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "audio.speak", "description": "TTS quote (dry-run, free) or live render (needs approved grant, burns package credits ~1/byte)",
     "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}, "voice_id": {"type": "string"}, "live": {"type": "boolean"}, "grant": {"type": "object"}, "campaign": {"type": "string"}}, "required": ["text", "voice_id"]}},
    {"name": "audio.estimate", "description": "Free server-side media quote: image/video generation cost + validation (read-only, never generates)",
     "inputSchema": {"type": "object", "properties": {"kind": {"type": "string"}, "workspace_id": {"type": "string"}, "model_id": {"type": "string"}, "prompt": {"type": "string"}, "operation": {"type": "string"}}, "required": ["kind", "model_id", "prompt"]}},
    {"name": "audio.generate", "description": "Image/video generation: dry-run returns free estimate; live needs approved grant + expected_credits, human-gated",
     "inputSchema": {"type": "object", "properties": {"kind": {"type": "string"}, "workspace_id": {"type": "string"}, "model_id": {"type": "string"}, "prompt": {"type": "string"}, "operation": {"type": "string"}, "expected_credits": {"type": "integer"}, "live": {"type": "boolean"}, "grant": {"type": "object"}, "campaign": {"type": "string"}}, "required": ["kind", "model_id", "prompt"]}},
    {"name": "audio.studio.import", "description": "Import a script into Story Studio (free: background LLM structures chapters/casts/tags, poll status)",
     "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}, "name": {"type": "string"}}, "required": ["text"]}},
    {"name": "audio.studio.status", "description": "Story Studio project status: chapters, dirty counts, roster, jobs (free read)",
     "inputSchema": {"type": "object", "properties": {"project_id": {"type": "string"}}, "required": ["project_id"]}},
    {"name": "audio.studio.generate", "description": "Render Studio blocks: dry-run free quote; live needs approved grant, cached blocks free",
     "inputSchema": {"type": "object", "properties": {"project_id": {"type": "string"}, "chapter": {"type": "string"}, "live": {"type": "boolean"}, "grant": {"type": "object"}, "campaign": {"type": "string"}}, "required": ["project_id"]}},
    {"name": "audio.studio.export", "description": "Export Studio master: free quote without confirmed_credits; live needs approved grant + confirmed number",
     "inputSchema": {"type": "object", "properties": {"project_id": {"type": "string"}, "confirmed_credits": {"type": "integer"}, "live": {"type": "boolean"}, "grant": {"type": "object"}, "campaign": {"type": "string"}}, "required": ["project_id"]}},
    {"name": "channel.status", "description": "Per-entity channel read: thesis, chairs locked/open, brief, bank, formats, YT state (free read — ask me this per channel)",
     "inputSchema": {"type": "object", "properties": {"slug": {"type": "string"}}, "required": ["slug"]}},
    {"name": "audio.speak_free", "description": "Render TTS on the $0 free tier (pro quality, no credits, no grant) straight into the voice bank. ≤1500 chars. Logged, never billed.",
     "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}, "voice_id": {"type": "string"}}, "required": ["text", "voice_id"]}},
     {"name": "audio.request", "description": "Ask to spend: quotes + freezes payload + files a human approval task (never spends). Human approves in dash queue, fulfill executes.",
      "inputSchema": {"type": "object", "properties": {"kind": {"type": "string"}, "text": {"type": "string"}, "voice_id": {"type": "string"}, "media_kind": {"type": "string"}, "workspace_id": {"type": "string"}, "model_id": {"type": "string"}, "prompt": {"type": "string"}, "expected_credits": {"type": "integer"}}, "required": ["kind"]}},
     {"name": "audio.cast.prepare", "description": "GO button for a collection: ensemble briefs + top-3 candidates per speaker + $0 audition each into the bank. Free reads + free renders only.",
      "inputSchema": {"type": "object", "properties": {"collection": {"type": "string"}, "channel": {"type": "string"}}, "required": ["collection"]}},
     {"name": "taste.profile", "description": "Owner taste profile: learned feature weights + standing rules compiled from locks/likes/anchors/notes (free read — check this before proposing voices)",
      "inputSchema": {"type": "object", "properties": {}, "required": []}},
    {"name": "channel.list", "description": "List all YouTube channels: studio + damn houses (read-only)",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "channel.skill", "description": "Channel skill pack: routines, style bible, laws, how-to-make (read-only, live docs)",
     "inputSchema": {"type": "object", "properties": {"slug": {"type": "string"}}, "required": ["slug"]}},
    {"name": "fable.packs", "description": "List vid packs with factory readiness (read-only)",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "fable.pack", "description": "One vid pack: meta + cue + prompts + build files (read-only)",
     "inputSchema": {"type": "object", "properties": {"slug": {"type": "string"}}, "required": ["slug"]}},
    {"name": "fable.pull", "description": "Pull pack + audio from R2 to box workdir (needs R2 creds)",
     "inputSchema": {"type": "object", "properties": {"slug": {"type": "string"}}, "required": ["slug"]}},
    {"name": "fable.push", "description": "Push stills + final to R2 (needs R2 creds, final must exist)",
     "inputSchema": {"type": "object", "properties": {"slug": {"type": "string"}}, "required": ["slug"]}},
    {"name": "fable.build", "description": "Assemble pack to full MP4 (async jid; stills + baked segments required)",
     "inputSchema": {"type": "object", "properties": {"slug": {"type": "string"}}, "required": ["slug"]}},
    {"name": "fable.job", "description": "Poll a fable build job",
     "inputSchema": {"type": "object", "properties": {"jid": {"type": "string"}}, "required": ["jid"]}},
    {"name": "fable.gate", "description": "Deterministic video gates on a built pack (PASS/FAIL + receipt)",
     "inputSchema": {"type": "object", "properties": {"slug": {"type": "string"}, "channel": {"type": "string"}}, "required": ["slug"]}},
    {"name": "qc.text", "description": "Slop gate on a channel text: coherence, rhythm, NoSlop signal + suggested edits (PASS/FAIL)",
     "inputSchema": {"type": "object", "properties": {"slug": {"type": "string"}, "file": {"type": "string"}}, "required": ["slug", "file"]}},
    {"name": "qc.audio", "description": "Delivery check on a rendered master: WPM vs chair spec + pauses vs direction tags (PASS/FAIL)",
     "inputSchema": {"type": "object", "properties": {"slug": {"type": "string"}, "audio": {"type": "string"}, "words": {"type": "integer"}, "wpm_target": {"type": "number"}, "drama": {"type": "string"}}, "required": ["slug", "audio", "words"]}},
    {"name": "fable.still", "description": "Tableau prompt for a tale (dry-run copy-paste until vision key lands)",
     "inputSchema": {"type": "object", "properties": {"slug": {"type": "string"}, "tale": {"type": "string"}}, "required": ["slug", "tale"]}},
    {"name": "r2.ls", "description": "List R2 prefix (read-only, needs R2 creds)",
     "inputSchema": {"type": "object", "properties": {"prefix": {"type": "string"}}, "required": []}},
    {"name": "yt.upload", "description": "DRAFT ONLY: stage title/desc/tags/chapters manifest, never publishes",
     "inputSchema": {"type": "object", "properties": {"slug": {"type": "string"}}, "required": ["slug"]}},
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
    if name == "brand.delegate":
        slug = str(args.get("slug", "")).strip().lower()
        task = str(args.get("task", "")).strip()
        if not slug or not task:
            return {"error": "slug + task required"}
        if "[delegated" in task.lower() or "[brand:global]" in task.lower():
            return {"error": "nested delegation refused"}
        if slug not in ("oddhobb", "pogtown", "humanvoiced"):
            return {"error": f"unknown entity {slug}"}
        try:
            import sys as _sys
            _sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from dash.agent_chat import agent_chat
            out = agent_chat(f"[brand:{slug}] [delegated] {task}", state=state, history=[])
            return {"result": {"slug": slug, "reply": out.get("reply", ""),
                               "tools_used": out.get("tools_used", [])}}
        except Exception as e:
            return {"error": str(e)[:200]}
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
            # Channel fallback: studio channel records inhabit like brands
            # (voice chairs, style lock, formats). Path-traversal guarded.
            if not slug.replace("-", "").replace("_", "").isalnum():
                return {"error": f"unknown brand {slug}"}
            try:
                with open(os.path.join(root, "influence", "studio",
                                       "channels", f"{slug}.json")) as f:
                    c = json.load(f)
            except Exception:
                return {"error": f"unknown brand {slug}"}
            chairs = (c.get("voice") or {}).get("chairs", {})
            return {"result": {
                "slug": slug, "display_name": c.get("display_name", slug),
                "domain": "youtube.com",
                "email": "", "kind": "youtube-channel",
                "handles": {"primary": f"@{slug}"},
                "voice": c.get("pitch", ""),
                "thesis": c.get("thesis", ""),
                "audience": c.get("audience", ""),
                "sourcing": c.get("sourcing", {}),
                "style_lock": c.get("style", {}),
                "thumbnail": c.get("thumbnail", {}),
                "formats": c.get("formats", []),
                "chairs": {n: {"label": (v.get("label", "") if isinstance(v, dict) else ""),
                               "locked": bool(isinstance(v, dict) and v.get("fish_id")),
                               "direction": (v.get("direction", "") if isinstance(v, dict) else "")}
                           for n, v in (chairs.items() if isinstance(chairs, dict) else [])},
                "branches": [{"platform": "youtube", "handle": f"@{slug}",
                              "status": "pilot",
                              "content_types": ["longform", "short"]}],
                "publish_gate": "human_confirm",
                "instructions": (f"Inhabit {c.get('display_name', slug)}: {c.get('pitch', '')} "
                                 f"Drafts only — publish stays human_confirm. "
                                 f"Locked voices only; propose 5 for open chairs.")}}
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
    if name == "etsy.listing":
        try:
            import sys as _sys3
            _sys3.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from pipeline.etsy_listing import preview
            return {"result": preview(str(args.get("store") or "oddhobb"),
                                      str(args.get("sku") or ""))}
        except Exception as e:
            return {"error": str(e)[:250]}
    if name in ("pack.list", "pack.compile", "release.create", "task.status", "campaign.list", "actions.list",
                 "images.plan", "images.generate", "images.upload",
                 "audio.voices", "audio.voice", "audio.balance", "audio.speak",
                 "audio.estimate", "audio.generate",
                 "audio.studio.import", "audio.studio.status",
                 "audio.studio.generate", "audio.studio.export",
                 "channel.status", "audio.speak_free", "audio.request",
                 "audio.cast.prepare", "taste.profile"):
        try:
            import sys as _sys2
            _sys2.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            if name == "pack.list":
                if str(args.get("legacy") or "") == "1":
                    from pipeline.compilers.pack_loader import list_packs
                    return {"result": list_packs(str(args.get("store") or "oddhobb"))}
                from pipeline.catalog import list_packs
                return {"result": list_packs(args.get("level"))}
            if name == "pack.compile":
                from pipeline.runner import preview_pack
                sku = str(args.get("sku") or "")
                if not sku:
                    return {"error": "sku required"}
                return {"result": preview_pack(sku, str(args.get("brand") or "oddhobb"),
                                               str(args.get("channel") or "etsy"))}
            if name == "release.create":
                from pipeline.runner import run_pack
                sku = str(args.get("sku") or "")
                if not sku:
                    return {"error": "sku required"}
                return {"result": run_pack(sku, str(args.get("brand") or "oddhobb"),
                                           str(args.get("channel") or "etsy"),
                                           args.get("campaign"))}
            if name == "task.status":
                from pipeline.effects import get_task
                t = get_task(int(args.get("task_id", 0)))
                if not t:
                    return {"error": "unknown task"}
                return {"result": {"task_id": t["id"], "state": t["state"],
                                   "brand": t["brand"], "kind": t["kind"],
                                   "payload_hash": (t.get("payload_hash") or "")[:16],
                                   "receipt_id": t.get("receipt_id"),
                                   "decision": t.get("decision")}}
            if name == "campaign.list":
                from pipeline.campaign import list_campaigns
                return {"result": list_campaigns(args.get("brand"))}
            if name == "actions.list":
                from pipeline.actions import list_actions, totals
                return {"result": {
                    "actions": list_actions(args.get("channel"), args.get("campaign"),
                                            args.get("status"), int(args.get("limit") or 20)),
                    "totals": totals(args.get("campaign")),
                }}
            if name in ("images.plan", "images.generate", "images.upload"):
                from pipeline.images_flow import plan, generate, upload_batch
                store = str(args.get("store") or "oddhobb")
                sku = str(args.get("sku") or "")
                if not sku:
                    return {"error": "sku required"}
                if name == "images.plan":
                    return {"result": plan(store, sku, str(args.get("provider") or "cloudflare"))}
                live = args.get("live") is True
                grant = args.get("grant")
                ctx = {"grant": grant} if grant else None
                if name == "images.generate":
                    return {"result": generate(store, sku, args.get("slots"),
                                               str(args.get("provider") or "cloudflare"),
                                               dry_run=not live, ctx=ctx)}
                return {"result": upload_batch(store, sku, args.get("items"),
                                               dry_run=not live, ctx=ctx,
                                               campaign=args.get("campaign"))}
            if name in ("audio.voices", "audio.voice", "audio.balance",
                        "audio.speak", "audio.estimate", "audio.generate"):
                from pipeline.audio_flow import (voices, voice_detail,
                                                 balance, speak,
                                                 estimate_media,
                                                 generate_media,
                                                 studio_import,
                                                 studio_status,
                                                 studio_generate,
                                                 studio_export)
                if name == "audio.voices":
                    return {"result": voices(str(args.get("query") or ""),
                                             str(args.get("language") or ""),
                                             bool(args.get("self")),
                                             int(args.get("page_size") or 10))}
                if name == "audio.voice":
                    return {"result": voice_detail(str(args.get("voice_id") or ""))}
                if name == "audio.balance":
                    return {"result": balance()}
                live = args.get("live") is True
                grant = args.get("grant")
                ctx = {"grant": grant} if grant else None
                if name == "audio.speak":
                    return {"result": speak(str(args.get("text") or ""),
                                            str(args.get("voice_id") or ""),
                                            dry_run=not live, ctx=ctx,
                                            campaign=args.get("campaign"))}
                if name == "audio.estimate":
                    return {"result": estimate_media(
                        str(args.get("kind") or ""),
                        str(args.get("workspace_id") or ""),
                        str(args.get("model_id") or ""),
                        str(args.get("prompt") or ""),
                        str(args.get("operation") or "t2v"))}
                return {"result": generate_media(
                    str(args.get("kind") or ""),
                    str(args.get("workspace_id") or ""),
                    str(args.get("model_id") or ""),
                    str(args.get("prompt") or ""),
                    int(args.get("expected_credits") or 0),
                    dry_run=not live, ctx=ctx,
                    operation=str(args.get("operation") or "t2v"),
                    campaign=args.get("campaign"))}
            if name in ("audio.studio.import", "audio.studio.status",
                        "audio.studio.generate", "audio.studio.export"):
                live = args.get("live") is True
                grant = args.get("grant")
                ctx = {"grant": grant} if grant else None
                pid = str(args.get("project_id") or "")
                if name == "audio.studio.import":
                    return {"result": studio_import(
                        str(args.get("text") or ""),
                        str(args.get("name") or "episode"))}
                if name == "audio.studio.status":
                    return {"result": studio_status(pid)}
                if name == "audio.studio.generate":
                    return {"result": studio_generate(
                        pid, str(args.get("chapter") or ""),
                        dry_run=not live, ctx=ctx,
                        campaign=args.get("campaign"))}
                cc = args.get("confirmed_credits")
                return {"result": studio_export(
                    pid,
                    confirmed_credits=int(cc) if cc is not None else None,
                    ctx=ctx, campaign=args.get("campaign"))}
            if name == "channel.status":
                import channel_onboard as _ob2
                return {"result": _ob2.channel_status(
                    str(args.get("slug") or ""))}
            if name == "taste.profile":
                sys.path.insert(0, os.path.dirname(os.path.dirname(
                    os.path.abspath(__file__))))
                from pipeline.taste_profile import load_profile
                p = load_profile()
                return {"result": {"ok": True,
                                   "n_features": len(p.get("weights", {})),
                                   "top": dict(list(
                                       p.get("weights", {}).items())[:20]),
                                   "rules": p.get("rules", [])[:10]}}
            if name == "audio.cast.prepare":
                sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                import sleep_studio as _st3
                coll = str(args.get("collection") or "")
                if (not coll.replace("-", "").replace("_", "").isalnum()):
                    return {"error": "bad collection"}
                return {"result": _st3.prepare_cast(
                    coll, str(args.get("channel", "") or "folk-and-fable"))}
            if name == "audio.speak_free":
                import time as _t3
                sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                from pipeline.audio_flow import speak_free as _sf
                text, vid = (str(args.get("text") or ""),
                             str(args.get("voice_id") or ""))
                if not text or len(text) > 1500:
                    return {"error": "text 1..1500 chars"}
                import sleep_studio as _st2
                nm = (f"pi-{_t3.strftime('%H%M%S')}.mp3")
                out = os.path.join(_st2.VOICE, nm)
                r = _sf(text, vid, out_path=out)
                if not r.get("ok"):
                    return {"result": r}
                meta = {"name": nm, "voice": f"pi:{vid}",
                        "backend": "free", "chars": len(text),
                        "credits_quoted": 0,
                        "url": f"/api/studio/file?kind=voice&file={nm}"}
                json.dump(meta, open(out + ".json", "w"), indent=1)
                return {"result": {"ok": True, **meta}}
            if name == "audio.request":
                from pipeline.audio_flow import audio_request as _ar
                kind = str(args.get("kind") or "")
                params = {"text": str(args.get("text") or ""),
                          "voice_id": str(args.get("voice_id") or ""),
                          "kind": str(args.get("media_kind") or "image"),
                          "workspace_id": str(args.get("workspace_id") or ""),
                          "model_id": str(args.get("model_id") or ""),
                          "prompt": str(args.get("prompt") or ""),
                          "expected_credits": int(
                              args.get("expected_credits") or 0)}
                return {"result": _ar(kind, params)}
        except Exception as e:
            return {"error": str(e)[:250]}
    if name in ("channel.list", "channel.skill", "fable.packs", "fable.pack",
                  "fable.pull", "fable.push", "fable.build", "fable.job",
                  "fable.still", "fable.gate", "r2.ls", "yt.upload",
                  "qc.text", "qc.audio"):
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import fable_ops as _fb
            if name == "channel.list":
                return {"result": _fb.channel_list(state)}
            if name == "channel.skill":
                return {"result": _fb.channel_skill(str(args.get("slug", "")))}
            if name == "fable.packs":
                return {"result": _fb.pack_list()}
            if name == "fable.pack":
                return {"result": _fb.pack_get(str(args.get("slug", "")))}
            if name == "fable.pull":
                return {"result": _fb.pack_pull(str(args.get("slug", "")))}
            if name == "fable.push":
                return {"result": _fb.pack_push(str(args.get("slug", "")))}
            if name == "fable.build":
                return {"result": _fb.fable_build(str(args.get("slug", "")))}
            if name == "fable.job":
                return {"result": _fb.fable_job(str(args.get("jid", "")))}
            if name == "fable.gate":
                return {"result": _fb.fable_gate(str(args.get("slug", "")),
                                                 str(args.get("channel") or "folk-and-fable"))}
            if name == "qc.text":
                return {"result": _fb.qc_text(str(args.get("slug", "")),
                                              str(args.get("file", "")))}
            if name == "qc.audio":
                return {"result": _fb.qc_audio(str(args.get("slug", "")),
                                               str(args.get("audio", "")),
                                               int(args.get("words") or 0),
                                               float(args.get("wpm_target") or 110.0),
                                               str(args.get("drama") or ""))}
            if name == "fable.still":
                return {"result": _fb.fable_still(str(args.get("slug", "")),
                                                  str(args.get("tale", "")))}
            if name == "r2.ls":
                return {"result": _fb.r2_ls(str(args.get("prefix") or "fable/"))}
            if name == "yt.upload":
                return {"result": _fb.yt_upload(str(args.get("slug", "")))}
        except Exception as e:
            return {"error": str(e)[:300]}
    return {"error": f"unknown tool {name}"}
