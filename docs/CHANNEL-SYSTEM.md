# Channel system — organisation map (2026-10-14)

One page for humans and agents: where everything lives, how it flows.

## The house rule

**influence = execution. damn = runbooks. sleepintel = strategy.
bgraph/bgraph2 = identity + memory. fish = engine.**

| Repo | Owns | Never owns |
|---|---|---|
| `prx0r/influence` | studio UI, prep, grants, renders, bank, receipts, channel records, MCP/pi | scripts (reads damn's), strategy (reads sleepintel's) |
| `prx0r/damn` | tale scripts, routines 01–07, pilots queue, validators (gate/poison) | audio renders, voice locks |
| sleepintel (local) | engines E1–E6, 238 registry, hypotheses, ideas queue | rendering |
| bgraph | brand branches, R2 layout, video items registry, validated exports | audio, scripts |
| bgraph2 | character seeds + instances + edges (memory) | distribution |
| fish (Fish Audio) | voices, TTS, Studio structuring, media models | our files, our decisions |

## Hierarchy (everything hangs here)

```
channel (studio/channels/<slug>.json)
  thesis · audience · sourcing · style · voices/chairs · cadence
  ├── series[] (s1-fairy 23 · s2-folklore 17 · s3-myth 4 …)
  │     narrator override · characters{} · thumbnail override · formats inherit
  ├── videos[] → bgraph registry/content/items/<id>.json
  │     (collection source · words/minutes · prep scores · voices · R2 · YT id slot)
  ├── dramatis/<book>.json (characters + profiles + voice queries)
  ├── casts/<collection>.cast.json (briefs + candidates + auditions)
  └── <slug>-brief.md / .seed.json / -taste.json
```

Configs inherit downward: series falls back to channel, videos to series.
Voices lock once per chair and propagate (never re-pick per video).

## Format tags (`studio/taxonomy.json` — tags are data)

talefull · excerpt · mythcrossover · andersensingle · systemrepeat.
Engines E1–E6. Status: scaffold → pilot → proven → live (blocked = needs
voice/source/key). Pi filters by tags; verdicts aggregate by tags.

## Flows (all $0 until owner says otherwise)

- **Cast:** propose 5 (tags + anchors + reasons) → tick/note → lock w/ reason
- **Prepare:** collection → ensemble briefs → top-3 per speaker → $0 auditions
- **Snippet:** prep → quote → approve → render → bank → human hears
- **Batch:** pilot → prep/gate/poison → per-speaker free renders → master → R2
- **Publish:** unlisted-first, human flips public (OAuth per channel, pending)
- **Verdict:** ship audio + black + 1 still → 30-day CTR/retention → etch or kill

## Market grounding (AvatarChannels intel, influence2, 681 channels)

Sleep niche: **zero competition**. Playbook: grandmother/female/senior
persona, 25–40min, 3–5/week, "[Name]'s Bedtime Stories" naming, $27 ebook +
$47–59 bundle + $9.90/mo circle. Persona gaps validate our slate:
mother (5), grandfather (9). Format norms: 15–20min sweet spot. Raw data:
`influence2/data/avatarintel/export.json`.

## Laws

0 credits ever (kill-switch, `CREDIT_SPEND_ENABLED` unset) · verbatim P0
(read the book) · one voice per project, never shared · free tier default,
Drama/credits only on explicit per-item yes · receipts for everything ·
secrets in vault/env, never in tree.

## Doors

- Studio: https://youtube.agentcom.org (channels as entities)
- Console: https://youtube.agentcom.org/classic and https://agentcom.org
- Bank/R2: voice bank in studio; masters archive to private R2 (presigned playback)
