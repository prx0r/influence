# Final Stack — who owns what and why

> 2026-10-10. The box has ~200 repos. This doc draws the boundaries so
> work stays organised. One rule: **influence/ is the runtime. Everything
> else is a worker, library, or source of truth. No code duplication —
> import, don't copy.**

---

## Layer map

```
┌─────────────────────────────────────────────────────────────┐
│ LAYER 1 — IDENTITY (who are the brands?)                    │
│ bgraph/                    brands, handles, domains, spine   │
│ oddhobbies/stores/*/store.json  commerce identity per store │
└─────────────────────────────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│ LAYER 2 — COMMERCE TRUTH (what do we sell?)                 │
│ oddhobbies/stores/*/listings/*.json  37 product packs       │
│ oddhobbies/docs/oddhobbsuppliers.md  supplier network       │
│ pogpet/backend/config.py   site-side pricing, ETSY_LISTINGS │
└─────────────────────────────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│ LAYER 3 — CONTENT FACTORIES (workers, not runtime)          │
│ content/       signals → 9:16 MP4 + receipts  (data stories)│
│ sleepdraw/     art → draw → R2 + recipe.json  (slow video)  │
│ pogpet creative/  capability router → fal/alibaba/local     │
│ sleepintel/    PATTERN SOURCE for operator (don't copy code)│
└─────────────────────────────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│ LAYER 4 — CHANNEL OPERATOR (influence/pipeline/)            │
│ pack_loader    pack → validated payload                     │
│ compilers/     pack → channel-native (etsy/shopify/pin/...) │
│ scheduler      per-account queue + cooldown + budget        │
│ analytics      metrics pull → ledger → re-rank              │
│ campaign.py    orchestrate compile→confirm→push→verify       │
└─────────────────────────────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│ LAYER 5 — PUBLISHING (workers, stevejobless/)               │
│ stevejobless/publisher/adapters/  X/IG/TikTok/YT/FB/LinkedIn│
│ stevejobless PostQueue + scheduler  queue + fire            │
│ Postiz wrapper  (only if adapter missing)                   │
└─────────────────────────────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│ LAYER 6 — VERIFICATION (qprivately + pipeline/verifiers/)   │
│ qprivately/acom/  gates, grants, receipts, runs (SPEC)      │
│ pipeline/verifiers/  G1-G5 + qc-* per channel (IMPL)        │
│ pipeline/gates/  human_confirm, spend (IMPL)                │
└─────────────────────────────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│ LAYER 7 — HUMAN + AUDIT (influence/dash/)                   │
│ human_actions  tasks, walk_prompt, approve/reject           │
│ notifications  bell + SMS + email                           │
│ suppliers  entities + email threads + chase                 │
│ actions  audited ledger ($0.005 fal calls visible)          │
│ receipts.jsonl  QP chain                                    │
│ campaigns  (to build)                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Why this split

| Decision | Why |
|---|---|
| bgraph owns identity | Single spine for handles/domains. Dash reads, never writes identity. |
| oddhobbies owns packs | Commerce truth. Compilers read packs, never invent values. |
| Factories are workers | content/sleepdraw render on demand. Operator decides what to render. |
| Operator lives in influence | One scheduler, one queue, one budget per account. Not scattered. |
| Adapters stay in stevejobless | They're tested there. Influence imports them. No copy. |
| qprivately is spec-only | Never import runtime from it except acom/ kernel. No forks. |
| Dash is the only UI | All human interaction through agentcom.org. No side dashboards. |
| agentcom/ repo is docs | Public manual content. Not runtime. Don't confuse with dash. |

## What sleepintel contributes (pattern, not code)

sleepintel built the most mature operator loop on the box:
`theses → hypotheses → channels → pilots → metrics → re-rank → grow`.

We extract the pattern into influence:
- **Per-account state** (budget, threshold, cooldown, history, ledger)
- **Calibration** (predictions with thresholds, weights update on verdicts)
- **Effort economics** (rank by EV/effort, not EV)
- **Competitor breakdowns** (recipes to steal, one mechanism each)

We do NOT copy sleepintel code. Different domain (sleep channels vs product brands).

## What we do NOT build

- ❌ Second dashboard (pdash patterns in, pdash server out)
- ❌ Second ledger (content receipts stay in content/, action ledger in influence/)
- ❌ Second scheduler (stevejobless scheduler + influence operator merge, not parallel)
- ❌ Training infra, GPU hosting, workflow orchestration (rent from fal/Alibaba)
- ❌ Fooocus, IPAdapter_plus, InstantID (maintenance-only upstream)

## Implementation order (this session)

1. ✅ Actions ledger + API (done)
2. ✅ Suppliers + email threads (done)
3. ✅ Verification gates (done)
4. → Per-account state table (Clipping Bench lesson)
5. → Factory → queue bridge
6. → Analytics pull (YouTube first)
7. → Campaign tables + linkage
8. → Dash Actions/Suppliers/Campaigns tabs (UI)
9. → Grant endpoints + spend caps
