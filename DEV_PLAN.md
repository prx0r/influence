# Influence — dev plan: shared QP primitive from step 0

Goal: rewrite cmail + pmail as one system on the dependency graph spine, dashboard live from step 0 so every phase is testable in the browser. No framework. Stdlib backend, static HTML, same queue everywhere.

This is the co-dev plan. We build in lockstep. Nothing lands unless you can see it in the dash and click it. If the dash doesn't show it, it isn't done.

## Where the law comes from

- `qprivately` is law: `SPEC.md`, 7 objects, one equation `S_{t+1} = T(S_t,P) iff ∧ G_i = PASS`, TransitionReceipt as sole state path, append-only store, versioned gates, fail-closed grants, 15 invariants. `acom/` is stdlib-only, no domain concepts.
- `qpfinal` is the discipline: processors propose, never settle. HLoop present-before-decide with banked prediction. Harbor stays eval-only, rewards imported as evidence. No self-promotion. Tournament + hidden tests decide promotion.
- `pmail` is the privacy + proof donor: actuality TRUE/FALSE/UNKNOWN with FALSE > UNKNOWN > TRUE, attempt vs independent readback, exact grants with payload hash + expiry + single use, journal-before-act, privacy compose + forbidden traits, Merkle evidence + public receipts, per-direction bridges, MCP advertises only what it can dispatch.
- `cmail` is the graph spine: Project + passport, connectors observe / optionally apply, reconcile writes ResourceState + HumanActions, autopilot observe-act-verify, RunLog receipts everything.
- `qpbot/dashboard` is the style reference: VSCode-like shell, lightweight, functional. No design system work. Function first.

Influence is the first workload that earns its history on top of that stack.

## Dashboard contract: qpbot style, function first

Same shell as `qpbot/dashboard/static/index.html`, already ported to `dash/static/index.html` (see `ATTRIBUTION.md`). Keep it boring and fast:

Layout, left to right:

- Activity bar 48px: Chat, Influencers, Vault, Tasks (+badge), Terminal. Switches sidebar only. Never navigates away.
- Sidebar 260px: context for the active icon. Chat shows commands + add form. Influencers shows `READY/total` per slug. Vault shows deposit form + key metadata, never values. Tasks shows queue with digit buttons.
- Center editor: tabs (`monitor` + one per influencer). Monitor shows runs. Influencer tab shows name, stage, progress bar, resource rows with READY/MISSING/BLOCKED/UNKNOWN/ERROR pills + message. This is the thin render remote. Backend owns truth and audit.
- Bottom panel 180px: Output / Tasks / Runs tabs. Log tails, reconcile summaries, decide results. Monospace, timestamped, `info/ok/err` colors.
- Right third, chat panel 320px resizable 200–600: Operator column. Always useful. Chat messages + `/add /status /help` + hero task approve/deny. This third is the control surface, not decoration. Same task IDs as sidebar, center, bottom, and MCP.

Rules for the dash:

- Static HTML + vanilla JS, no build step, no deps. Polls `/api/state` every 15s. Same endpoints MCP uses.
- Token gate: `?token=` required when `DASH_TOKEN` set. Binds 127.0.0.1. Tunnel only via `serve.sh --tunnel`. Capabilities never leave the server. Secret-scan before push.
- One purpose per view, one tab per job. New needs start as one tab showing run + evidence root + receipt + approve-deny. What HTML does not do — realtime sockets, drag planning, offline push, in-page signing, bulk files — stays in daemon/server/native.
- Backend computes, dash displays. The mxth-style pattern holds: page is approval + render remote.

Run it:

```bash
./dash/serve.sh            # loopback, prints token URL
./dash/serve.sh --tunnel   # + cloudflare quick tunnel
python3 dash/test_dash.py  # stdlib-only, health + shape + decide + mcp + chat + vault + gate
LIVE_TEST=1 python3 dash/test_dash.py  # + live reconcile shape
```

Current baseline passes: health, state, tasks, decide, mcp, chat, vault, gated 403/200.

## How we work together

We stay in lockstep. I don't run ahead. Each step is: small backend diff + dash-visible proof + tests green + you click it in the browser.

Session loop:

- I propose one slice. You run `./dash/serve.sh`, open the token URL, confirm the exact manual check listed.
- You say `ok` or `fix X`. I fix, you re-check. Then we move.
- Either of us can call `stop, dash is behind` — that means backend work pauses until the dash shows it.

Definition of done for every slice: `python3 dash/test_dash.py` green, manual dash check you performed, no secrets in tree, receipt or reconcile visible where claimed. Human approval is intent only, never QP authority. Drafts everywhere, spends/sends behind tokens + task approval.

## Phase 0 — step-0 dash (done, keep green)

`dash/server.py` stdlib ThreadingHTTPServer mirroring qpbot shape. `GET /api/health`, `GET /api/state` from `seed.json` (LIVE=0) or `dash/store.py` live reconcile (LIVE=1). Seed: nova-ink name-only, velvet-signal domain-owned, copper-field wired-needs-content. Tasks T-001..T-003 map 1:1 to resource keys.

Your check: three cards with progress bars, hero task with 7/1 digits, rail, log tail all render. Token URL works, no-token gets 403 when gated.

## Phase 1 — kernel transplant: literal qp math (next, clean restart of kernel only)

Problem: `core/cmail/engine.py` writes DB rows directly. `qp/` helpers sit alongside, not under the equation. Not literal proof math yet.

Do not start a new repo. Keep dash, seed, docs, `port/` pins. Replace kernel internals only:

- Vendor-pin `qprivately/acom` as law, import it, never copy it. No duplicate definitions, no domain concepts in the kernel copy.
- Reconcile becomes adapter: connector observation -> `make_evidence`, resource -> `make_claim` TRUE/FALSE/UNKNOWN, reconcile -> `receipts.transition()` with `two-sources-v1 + claim-resolved-v1 + evidence-fresh-v1 + no-duplicate-v1` plus influencer gates, journal -> `Store.append/replay/verify_chain`, authority -> `acom.grants.verify_grant`, dash `/api/state` replays from store.
- Statuses stay as observations, actuality says what is proven. MISSING stays UNKNOWN, never FALSE.

Tests: kernel tamper fails, unknown gate fails, unsigned grant fails, FAIL receipt stored, settle re-executes from bytes, port byte-identical checks still pass.

Dash proof: influencer tab gains evidence root + receipt id per run. Monitor tab shows `passed` + gate list. Same pills, plus proof.

Your check: open an influencer, see receipt id + evidence root. Run reconcile from Terminal sidebar, see new run in monitor with gates listed. Break something on purpose (bad domain), see FAIL receipt not silent error.

Stop rule: no Phase 2 connectors until you have clicked a PASS and a FAIL receipt in the dash.

## Phase 2 — verticals as passports

cmail surfaces become connector sets, not forks: domain, website, social, postiz, mail, number/phone, tradie preserved. Influencer passport: candidates, handles map, domain verify DNS+RDAP, registrar compare, prepare-approve-register-wire with drift + budget guards, zone, mailbox, number via bridges, social verify, content. pmail bridges arrive as capability-matrix providers with lifecycle + hard-filter selection. Import script reads existing passports, one reconcile, missing pieces surface as tasks.

Tests: connector never raises, passport validates, import idempotent, dry-run asserts task chain order.

Dash proof: per-influencer graph view, resource rows with next-step copy. `/add slug domain` works from chat panel and shows up in sidebar + center + bottom together.

Your check: `/add testinfluence testinfluence.dev`, watch it appear, click through its resources, confirm tasks match missing pieces.

## Phase 3 — MCP + human loop

Read-only MCP first: `influencer.list/get`, `queue.list` over graph, quarantine excluded. Writes stay on REST behind approval tokens + H-task. HLoop from qpfinal: present-before-decide, banked prediction hash, digit resolution, sealed artifacts, autonomy ladders per family, never-auto classes (authorization, secret, identity, physical, ambiguity) enforced, leases for parallel work. Subagent spawn/monitor/audit as worker layer for intake + drafts.

Tests: tools/list equals dispatchable surface, unknown tool rejected, quarantine never in corpus, grant checks on consequential tools, prediction-must-precede-answer, single-use prediction, demotion on failure, subagent timeout/crash.

Dash proof: hero card in right third gains digits + seal-payload, runs view gains budget + approve-deny `APPROVED_PENDING_QP` -> `QP-authorized`. Bottom panel shows present ref + decide result.

Your check: present then decide a task from the Tasks sidebar, see `APPROVED_PENDING_QP`. Try decide without present, see 409. Confirm prediction ref single-use.

## Phase 4 — Cloudflare host

Worker serves same static + `/api/*` proxied to brain (tunnel first, then split reads/writes), D1 state mirror, R2 raw evidence + backups. Deploy via vault-run wrangler, tokens from oracle vault, nothing in tree. Email Routing cutover stays explicit human task.

Tests: wrangler dry-run, preview URL smoke, backup/restore drill, secret-scan CI blocking push.

Dash proof: same UI on preview URL, same token gate, same task IDs.

Your check: open preview URL, confirm same three influencers + queue as local.

## Phase 5 — management extension

Same queue switches to operate: content calendar via publisher/postiz, inbox triage needs-reply, deals + renewals, calibration + RSI reweighting, reputation from verified runs under tree head. New lenses one tab at a time: kaggle backend + display, mxth specimens, spend board. Each lens one static view over same task IDs.

Tests per lens: backend owns truth + audit, page renders approvals + receipts.

Dash proof: new tab appears with run + evidence root + receipt + approve-deny, nothing else moves.

Your check: per lens, same as Phase 1 — see it, click it, approve/deny it.

## Standing rules

Additive to live cmail surfaces until cutover. Drafts everywhere, spends/sends behind tokens + task approval. Secrets in vaults/env only. Attempt is not observation. Human approval is not QP authority. Small diffs, verified before claimed. Dashboard stays the test harness — if it is not visible in the dash, it is not done.

## File map

- `dash/server.py` — stdlib server, token gate, routes. `dash/store.py` — live reconcile. `dash/seed.json` — step-0 truth. `dash/static/index.html` — qpbot shell port. `dash/test_dash.py` — our contract.
- `core/` — graph adapter (imports `qprivately/acom`, never forks it). `qp/` — thin wrappers only after Phase 1. `port/` — byte-identical references + `SOURCES.md` pins.
- `qprivately/SPEC.md + docs/` — law. `qpfinal/docs + human/hloop` — HLoop + Harbor patterns. `pmail/src` — privacy/authority/journal reference. `qpbot/dashboard` — style reference.
