# SOURCES — every outside repo, what we take, where it lives now

Read this instead of nine repos. Rule: influence never reimplements a
kernel, never pastes licensed code — it vendors law (drift-guarded),
calls live services, and reimplements only patterns.

| Repo | We take | Lives here now | Pin / live URL |
|---|---|---|---|
| qprivately | QP law: 7 objects, 1 equation, TransitionReceipt, store, gates, grants | `law/acom/` (vendored, drift test) | `c18433a`, acom/0.1 |
| qp | killfeed/circuit + crypto patterns (reference impl, not law) | patterns only, nothing copied | main `21588f7` era |
| cmail | graph spine (passport/reconcile/tasks), domain buy machine, Telnyx shape, checker research | `core/`, `port/` pins, `docs/*.md` syntheses | base `583cd62` |
| domainnamechecker (in cmail) | LIVE name-intel service: verify, registrar compare, handles, claim_kit, mine | called, not copied (`names` connector) | https://domainnamechecker.tradesprior.workers.dev (v3.3.0) |
| pmail | privacy/authority/journal/spend patterns (actuality, exact grants, journal-before-act, drift rule) | `qp/authority|privacy|disclosure|journal|spend|session.py` (reimplemented) | master `8869a4a` era |
| qpbot | dashboard shell style, HLoop present→decide shape | `dash/static/` port + `dash/hloop.py` (reimplemented) | see `dash/static/ATTRIBUTION.md` |
| pq | logged-testing discipline (runs/ JSONL + receipt per finding) | `experiments/live_*.py`, `runs/` (gitignored) | README rules 1–5 |
| qpfinal | discipline language (processors propose, verifiers judge, humans bound risk) | `DEV_PLAN.md`, `qp-protocol.md` | uncommitted archive, cite don't copy |
| freaktown | stage/performer bundles, Ella judge (future leaf) | designed, not wired (`products/influencer-studio.md`) | — |
| etsysignal | roast.pet storefront pipeline (future leaf) | designed (`products/roast.pet.md`) | — |

Live surfaces: dash https://influence.intelligentothers.xyz (named tunnel
`influence-dash` → loopback 8793). Secrets: agent-vault `oracle` /
`cloudflare` vaults + env only, never in tree.
