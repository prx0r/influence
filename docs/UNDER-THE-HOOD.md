# UNDER THE HOOD — how the system fits together

## The spine: entity is the selector

Every graph keys off one slug (`oddhobb`, `pogtown`, `humanvoiced`):

```
slug ──┬── bgraph/registry/brands/{slug}.json  (identity, voice, branches, gates)
       ├── bgraph/exports/{slug}.json          (generated graph, lazy-regen if stale)
       ├── oddhobbies/stores/{slug}/store.json (commerce truth, socials, channels)
       ├── dash project {slug}                 (tasks, runs, receipts, passport)
       ├── mailbox hello@{domain}              (cmail worker → email.inbox)
       └── site BRANDS[host]                   (pogpet config.py brand_for)
```

`brand.voice {slug}` merges spine + commerce into the inhabit pack.
`brand.graphs {slug}` returns every graph handle. `brand.delegate {slug, task}`
runs a scoped subagent. New entity = same five files, nothing else.

## Request paths

- **Dash page** → Cloudflare tunnel → `127.0.0.1:8793` (ThreadingHTTPServer,
  stdlib). Static from disk per request (no restart for frontend edits);
  SQLite WAL + busy_timeout; `/api/state` falls back to last-good snapshot
  (`stale:true`) instead of failing on lock contention.
- **Chat** → `/api/chat {message, brand, history}` → deterministic verbs win,
  else mimo operator with read-only tools → intent judges. Brand selects the
  SYSTEM prompt; history threads previous turns.
- **Mail** → Cloudflare Email Routing → `cmail` worker (Durable Objects,
  R2 raw) → `email.inbox/read` MCP. SMS → Telnyx → phone worker → `phone.sms`.
- **X posting** → xman :3999 (Next + SQLite, 3 slots) → scheduler → X API
  (pay-per-use). Drafts in xman, human approves, scheduler posts.
- **Studio** → FableCut :7777 (JSON timeline, SSE live-reload, ffmpeg export);
  PhotoCraft :7778 (WASM editor). Agent drives both (MCP/file/CLI).
- **Publish gate** → `human_confirm` everywhere (bgraph law). Sends, spends,
  sanctions: human only.

## Data & truth rules

- bgraph = spine (describes). oddhobbies = product truth. pogpet = serves.
  influence = ops. Never invert.
- Secrets live in vaults; tree holds names (`auth_ref`). 0600 files, no
  commit of `.env`/tokens (gitignored + secret-scan rule).
- Events are truth: ledgers append-only (dash runs/receipts, workerkit
  chain-hash pattern, humanvoiced contract_events). Projections rebuild.
- Publish/renewals/adjudication: human-signed. Agents recommend, never enact.
