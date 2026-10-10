# Reuse Review — content / pdash / sleepdraw + external landscape

> 2026-10-10. Deep-read all three local repos + web search for comparable
> open-source systems. Verdict on what to reuse, what to mirror, what to skip.

---

## TL;DR

| Repo | Verdict | Action |
|---|---|---|
| **content** | REUSE PATTERNS | Lift `core/` ledger + gates + MCP tool shapes. Don't merge. |
| **pdash** | REUSE KERNEL, SKIP WRAPPERS | `acom/` verbatim. HTasks spec-only (broken). PactProof crypto is demo-grade. Decide canonical dash. |
| **sleepdraw** | KEEP + WIRE COSTS | Working engine. Import COSTS.md into `costs.py`. fal not wired (no key). |
| **External** | MINE, DON'T ADOPT | presswork + 626Labs validate the architecture. diplomat-gate/air-gate validate gates. Nothing to fork whole. |

---

## 1. content/ — the closest thing to our pipeline

**What:** Graph signals → scored → content spec → narration → 9:16 MP4 → hash-chained receipts → dash approve.

**Discrepancy found:** README claims 27 MCP tools. Code has **22** (`mcp_server.py:1539-1649`).

### Reuse (specific)
1. **`core/receipt.py`** — `append_receipt(kind,ref,status,detail)` + `verify_chain()`. Hash-chained JSONL with `prev/kind/status/ref/detail/at/receipt_id`. Tamper test in `tests/test_kernel.py`. **Lift verbatim** for our action ledger.
2. **`core/gates.py`** — `run_gates()` with `(bool,str)` tuple convention. Our G1-G5 + qc-* should follow this exact shape so tooling is interchangeable.
3. **`core/proof.py`** — `proof_from_signal` refuses metric-less/evidence-less inputs. Same refusal logic for packs missing price/cost.
4. **MCP tool shapes** — `ingest → compile → render → publish → measure` staged pattern. Our pack compiler should mirror: `pack_load → compile → push → verify → receipt`.
5. **`publish()` = manual-pending stub** — never auto-publishes. Human approve is the only transition to live. **Copy this rule.**
6. **Registry YAML** (`registry/templates.yaml`, `channels/*.yaml`) — add `channels/etsy.yaml`, `channels/pinterest.yaml` in the same schema.

### Don't reuse
- HyperFrames renderer (we use product renders, not 9:16 video)
- Hardcoded absolute paths (`/home/ubuntu/...` — not portable)
- Dash auth token in JS (hardcoded)
- `publish.youtube/instagram/tiktok/x/facebook` (registry-only stubs)

### Key lesson
`core/processor.py:run_processor` **rejects output keys** like `send|spend|mint|publish|post` — processors propose, never execute. This is the propose-only enforcement we need in our compilers.

---

## 2. pdash/ — reuse the kernel, skip almost everything else

**What:** qpbot dashboard fork + vendored QP kernel + PactProof + sub-agents + audit. Privacy/TEE-first.

### The critical finding: PactProof crypto is demo-grade
- `generate_keypair()` = `sha256(time)` — not Ed25519
- `verify_credential()` checks `len(sig)==64` — length only
- `api.py` **re-issues** credentials on prove/verify instead of loading originals
- Credentials stored as **plaintext JSON**
- `SECURITY.md` admits unforgeability is "simplified"

**Do not use PactProof crypto for anything real.** Use it as spec + predicate shapes only.

### HTasks: spec-only, broken
- DEVPLAN shows Authority pane (HTasks / 0–9 pad / Secrets / Grants / Spend)
- `dashboard/server.py:385` imports `agentcom.htasks.queue` — **module doesn't exist**, server crashes on `/api/answer`
- Only 2 seeded demo tasks in `runs/htasks.json`
- Real HTasks live in `pogpet/dash/agentcom/htasks/queue.py` (not vendored)

### What to reuse (specific paths)
1. **`acom/canonical.py, objects.py, gates.py, grants.py, receipts.py, store.py, crypto.py, ed25519.py`** — verbatim. Real RFC8032 Ed25519. One receipt format: `acom/0.1 TransitionReceipt`.
2. **`pdash/agentcom/vault/store.py:158` `record_usage()`** + `tracker.py:33` `cost_minor()` + `asynclog.py` UsageLogger — spend ledger with fcntl locking. **But:** caps in `pq.json` are never enforced — add the missing check.
3. **`pdash/agentcom/subagent.py:212` `spawn()`** — prompt-file + detached Popen + watchdog. Replace the 5 SUBAGENTS (wallet_hunter etc.) with brand workers.
4. **Dashboard HTTP skeleton** — token gate + ThreadingHTTPServer. Rewrite routes (most import missing qpbot modules).
5. **PactProof predicate shapes** — `history.py` count_at_least/value_sum/exists_with. Not the crypto.

### The dash question (needs owner call)
pdash and influence solve the same problem. Differences:
- pdash: privacy/TEE-first, CTF/crypto workers, VSCode-clone UI
- influence: brand-ops, live projects/suppliers/actions, ops-board UI

**Recommendation:** influence is canonical (live data, suppliers, audit list). Port pdash's HTasks/grants patterns into it. Don't run two dashes.

---

## 3. sleepdraw/ — keep as working visual worker

**What:** FLUX pencil art → 16:9 crop → skeleton-stroke draw → R2. ~2MB, CPU-only, $0 pipeline except fal bits.

### Costs (from COSTS.md — import these)
| Step | Cost |
|---|---|
| Art (CF FLUX) | $0 |
| Variant edit (fal flux-2) | **$0.024/img** |
| Breathe (fal i2v) | **$0.05–0.10/clip** |
| Bed (fal ACE-Step) | **$0.02–0.05/track** |
| Draw/render/ship | $0 |
| 10-min film all-in | **~$0.70** |

### Reuse (specific)
1. **`ship.py:publish()` + recipe.json** — same-basename sidecar with full env. Add `cost_usd` + `qc` fields. Cheapest audit trail.
2. **Locked recipe format** (`lora1.yaml`) — new preset file per SKU line, never silent tweaks. `AGENTS.md:28` drift rule.
3. **`assets/library.json` + `registry.json`** — variant casting pool (tag banked assets, reference tags not files).
4. **Sleep Studio tab** — already in influence dash, `sleep_studio.py` imports sleepdraw one-directionally. Add `studio.approve` verb before publish.
5. **30fps not 60fps** — halves files. Do before scaling to hundreds of variants.

### Status
fal NOT wired (no key, `breathe.py` doesn't exist). CF free tier covers art. Already integrated with dash.

---

## 4. External landscape (web search)

### POD pipelines (validate our architecture)

**brac/presswork** — 4-agent POD (Scout/Design/Listing/Ledger) via Supabase, fal FLUX, `HUMAN_REVIEW_ENABLED` gate. **Closest to our vision.** Mine: agent handoff via shared DB, SHA-256 dedup to avoid duplicate fal calls, per-order margin + low-margin Slack alerts.

**626Labs POD pipeline** — real Etsy shop, Gemini art → QA → Printify → Etsy. **Gates live in code** (`pod build` can't publish, `ship publish` walks drafts with per-product y/n). Mine: the gated publish pattern, AI-slop QA filter.

**digitalvendorxx/etsy-product-creator-v2** — Etsy SEO with NLP rules baked into prompts (title <70 chars, primary keyword first 30, 13 long-tail tags). Mine: tag pipeline scoring (competition + sales + views).

**worldofpasa/printpasa** — 7-stage, provider-agnostic, Telegram operator. Mine: provider-agnostic settings per stage.

**eisenheiim/Contentsy** — photo → SEO copy → Etsy draft. Mine: category playbooks with real taxonomy paths.

**ReitTech/UnicorePrints** — design library → listings overnight, self-healing agent, 134 tests. Mine: composition-key dedup guard, publish budget caps.

### Approval gates + audit (validate our gates)

**Diplomat-ai/diplomat-gate** — deterministic CONTINUE/REVIEW/STOP, hash-chained SQLite audit, framework adapters. **Best match for our G1-G5.** Mine: the verdict enum, review queue lifecycle.

**airblackbox/air-gate** — HMAC audit chain, EU AI Act Articles 12/14, Slack approve/reject. Mine: compliance report format.

**iflow-mcp/agent-receipts-ar** — signed receipts, MCP proxy, multi-language SDKs, local dashboard. Mine: the MCP proxy pattern (receipts without changing client/server).

**KaushikKC/AgentAudit** — Merkle trees, Ed25519, Sigstore anchoring, regulation-mapped export. Mine: the evidence bundle format (for when we need regulator-grade proof).

**venkateswarisudalai/agentgate + agentkitai/agentgate** — MCP gating with dashboards. Mine: the zero-agent-code-change wrapping pattern.

**IkaRiche/kilu-sdk** — ALLOW/REQUIRE_CONFIRM/BLOCK, Ed25519 receipts. Mine: the 3-state verdict (simpler than our 5 gates for simple actions).

**permission-protocol/deploy-gate** — Ed25519 receipts for deploys, fail-closed. Mine: "No receipt = No merge" rule.

### What to actually do with externals
**Mine, don't adopt.** Nothing to fork whole:
- presswork → agent handoff + dedup + margin alerts
- 626Labs → gated publish in code + QA filter
- diplomat-gate → CONTINUE/REVIEW/STOP verdict shape
- agent-receipts-ar → MCP proxy pattern
- etsy-product-creator → NLP tag rules

---

## 5. Consolidated reuse list (priority order)

| # | What | From | To |
|---|---|---|---|
| 1 | `acom/` kernel verbatim | pdash (→ qprivately) | influence pipeline |
| 2 | Receipt JSONL + verify_chain | content `core/` | action ledger |
| 3 | Spend ledger (record_usage + caps enforced) | pdash vault | pipeline costs |
| 4 | Gated publish in code | 626Labs + content | adapters (can't publish without gate) |
| 5 | COSTS.md entries | sleepdraw | `pipeline/costs.py` |
| 6 | Recipe-per-run sidecar | sleepdraw | every generated asset |
| 7 | MCP staged tools | content | pack compiler tools |
| 8 | Agent handoff via DB | presswork | campaign orchestration |
| 9 | Margin alerts | presswork | per-order economics |
| 10 | Sub-agent spawn skeleton | pdash | brand workers (replace configs) |

## 6. Do NOT reuse

- PactProof crypto (demo-grade: time-based keys, length-only verify, plaintext store)
- pdash HTasks (broken import, spec-only)
- pdash dashboard routes (most import missing modules)
- content's hardcoded paths, dash token in JS
- sleepdraw fal integration (doesn't exist yet — docs only)
- Any external repo whole (mine patterns, don't fork)
- Fooocus, IPAdapter_plus, InstantID (maintenance-only upstream)

## 7. Open decisions

1. **Canonical dash:** influence (my vote) vs pdash — owner call
2. **Receipt format:** `acom/0.1` TransitionReceipt everywhere (my vote)
3. **FAL_KEY:** still missing — blocks all fal generation
4. **Qwen activation:** console step needed
5. **Shopify token:** stale — blocks Pinterest via sales channel
