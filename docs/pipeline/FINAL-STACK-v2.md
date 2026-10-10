# Final Stack — build vs buy per resource, with reasoning

> 2026-10-10. Every resource from the strategy brief, investigated.
> Decision per item: BUILD / BUY+WRAP / WATCH / SKIP, with why.
> Rule throughout: **rent capabilities, own verification + taste + history.**

---

## Generation layer (RENT — all of it)

| Resource | Decision | Reasoning | Integration point |
|---|---|---|---|
| **Meshy** (text/image→3D, texture, rig, animate) | BUY+WRAP | Credit pricing verified (20 mesh + 10-15 texture, rig 5, anim 3/action). Our `pogpet/backend/meshy.py` already wraps with ask-first + ledger. No MESHY_API_KEY yet — human task. | `creative/providers/` already has the slot. Add spend to `costs.py`. |
| **Google Playground** (prompt games) | WATCH | Launched Oct 7, no API dependency. Don't compete. | None. Weekly watch. |
| **Unity Spark** | WATCH | Closed beta, no API/economics. Don't build on it. | None. Weekly watch. |
| **World Labs Marble** (3D scenes) | SELECTIVE | Meshes not manufacturing-grade. Useful for room design only. | Later, via capability router. |
| **Mixamo** (auto-rig + animations) | USE | Free reusable humanoid animation. Check asset licensing per use. | Character pipeline when needed. |
| **fal.ai** (model supermarket) | BUY+WRAP | Already in router. Needs FAL_KEY. | `costs.py` has prices. |

## Character / voice / realtime (RENT infrastructure, OWN identity)

| Resource | Decision | Reasoning | Integration point |
|---|---|---|---|
| **OpenCharaAgent** (persistent characters) | EVALUATE | Memory/tools/schedules useful, but Pog identity contract is ours. Don't clone blindly — extract patterns. | Compare against Pog interface before adopting. |
| **AI VTuber ecosystem** | EVALUATE RENDERERS | Many runtimes exist. We need one renderer, not a framework. | Pick one when P1 needs it. |
| **LiveKit Agents** (realtime voice) | BUY+WRAP | Mature, parked behind keys in our todo. Don't build transport. | `pogpet` voice rooms when keys land. |
| **Nakama** (multiplayer) | SKIP until needed | Established, integrate only when multiplayer is real. | None now. |
| **Muse Gadget SDK** (ESP32 agents) | ADAPTER (later) | Optional. Build thin adapter when hardware exists. | P2 hardware reference. |
| **ESPHome** (device firmware) | USE for first hardware | Standard firmware + HA compat. Don't write transport protocols. | GlowBase reference (P2). |

## Manufacturing back office (BUY the system, OWN the data)

| Resource | Decision | Reasoning | Integration point |
|---|---|---|---|
| **InvenTree** (parts/BOM/builds/inventory) | EVALUATE → likely ADOPT | Full REST API (DRF, token/OAuth), BOM with validation checksums, build orders, suppliers, substitutes, multi-level BOMs. Self-hosted Docker. **This is our manufacturing back office** — don't build one. | Spike: Docker deploy → create 1 part + BOM via API → link supplier entity. If API fits, adopt. |
| **InteractiveHtmlBom** | REUSE | BOM visualisation + assembly assistance. Free, focused. | Link from job packets. |
| **JLC API** (PCB/3D quote+order) | PRIORITY INTEGRATION | Already in supplier entities. API approval needs order history — submit prototype order alongside application. | `pipeline/suppliers.py` jlc entity + job packets. |

## What we BUILD (layers 3–5, the moat)

| System | State | Why it's ours |
|---|---|---|
| **Learn loop** (Jev judges → stats → weights → briefs) | ✅ Built today (`learn.py`, packs, BH/power) | Taste is proprietary. No vendor sells our audience's preferences. |
| **Verification gates** (G1-G5 + qc-*) | ✅ Built | Reliability is the product. Nobody else verifies our pipeline. |
| **Manufacturing compiler** (pack → job packet → supplier) | Spec'd (oddhobbsuppliers.md §6) | Coordination across suppliers is the hard part. |
| **Channel operator** (budgets, cooldowns, queue, metrics) | ✅ Built today (`channel_state.py`) | Account health is operational knowledge. |
| **Supplier entities + email** | ✅ Built today (`suppliers.py`) | Relationship history accumulates. |
| **Audit ledger** (every action + cost) | ✅ Built today (27 rows) | Commercial truth. |
| **Pog identity contract** | Spec'd (strategy §6) | Portability across engines. Small, keep frozen. |
| **Opportunity radar** (P3) | Spec'd | Demand detection → manufacturing offers. Builds on Data Gardens. |

## What stays FROZEN (explicit no-build list)

General game creation · custom graphics engines · general agent memory frameworks · proprietary multiplayer · model training · massive asset catalogues · advanced robotics · simulated Pogtown society · Unity Spark production · Mutuals/Kaigen (watchlist, unverified).

## Weekly watch (report only build-vs-buy changes)

Google/Unity Spark (API? economics?) · character runtimes · Muse hardware projects · manufacturing APIs (JLC/Seeed/Elecrow changes) · Meshy pricing/model retirements (lowpoly dies Oct 30).

## The one paragraph

Rent every capability that regenerates (models, meshes, voices, games, firmware transports, inventory software). Build everything that accumulates (taste weights, verification receipts, supplier performance, character histories, fulfilment outcomes). The company is not the code — it's the verified history of what worked, who delivered, and what audiences loved.
