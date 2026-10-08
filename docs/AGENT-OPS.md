# AGENT-OPS — how an agent operates here (pi, dash operator, subagents)

## The loop

```
brand.voice {slug}   → inhabit: voice, style_lock, handles, gates
brand.graphs {slug}  → see: exports, packs, project, primitives
work the task        → drafts, reads, comparisons — never sends/spends
human confirms       → digit/button/vault seal in dash, approval in xman
receipts prove it    → runs, receipts, R2 sinks
```

## Laws (no exceptions)

1. **Slug first.** Every fact belongs to exactly one entity. If the brand is
   ambiguous, ask — never guess, never mix oddhobb/pogtown/humanvoiced.
2. **Voice pack before claims.** Call `brand.voice` before stating handles,
   prices, or status. Kits/dash are fallback, never primary.
3. **Drafts only.** No post/send/buy/publish without explicit human confirm.
   Point at the exact button (▶ start, ✓, xman approve) instead.
4. **No secret touch.** Never print, log, or paste secrets. Guide the human
   to the vault box (name autofills from the active task). Values never enter
   chat, prompts, receipts, or files.
5. **Honest empty.** If a tool errors or returns nothing, say so and name the
   tool. Never invent tasks, prices, handles, or success.
6. **Cite sources.** Tool name + what it returned, boiled to what's useful
   (`x.com: 165075`, not the raw headers).
7. **Budgets are real.** X posts cost $0.015 ($0.20 with links). Meshy spends
   credits — ask every time. State the cost before acting.
8. **Subagents stay scoped.** `brand.delegate {slug, task}` runs one entity;
   nested delegation is refused. Global orchestrates, entities execute.

## Handoff protocol (global → entity)

Global receives the request, names the slug, and delegates:
`brand.delegate {slug: "pogtown", task: "check X inbox and draft 3 replies"}`.
The subagent answers in-entity-voice with findings + drafts. Global relays,
human approves per entity. Cross-entity comparisons name both slugs and
both sources.

## Startup checklist (new session)

1. `OPENCODE_API_KEY` from `~/.local/share/opencode/auth.json` (vault copy is stale).
2. Node 22 at `/opt/node22` for anything JS; stevejobless venv for dash python.
3. Check `df -h` (stay above 5G free) and `/api/health` on 8793/7777/7778/3999.
4. Read `docs/DEPENDENCIES.md` for what's running before touching anything.
