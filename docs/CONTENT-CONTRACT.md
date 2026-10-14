# Content contract v1 — damn ⇄ influence (2026-10-14)

Machine-readable twin: `studio/content-contract.json`. This doc is the
human version. Both lanes read both files; changes by agreement, never
unilateral (a format break orphans the other lane's automation).

## Direction of flow

damn produces → influence executes → bgraph remembers:

```
damn/projects/<house>/{pilots, videos, readout}/*.drama.txt
        │  (scripts + routines + gate/poison + verdicts)
        ▼
influence studio: prep → cast → render → bank → R2
        │  (audio + locks + seeds + receipts)
        ▼
bgraph registry/content/items/<video_id>.json
        (canonical video record both lanes reference)
```

## Script formats (damn writes, we parse — byte-exact)

**drama.txt** (pilots `NN-<slug>.drama.txt`, videos `NN-<slug>-<part>.drama.txt`):
- `//` header lines: project/season/title, SHIP line (model + chars),
  chair lines `// <chair> <|speaker:N|> <Label> <32-hex-id> (stand-in|locked)`,
  SFX spots (after voice lock only)
- Body: `<|speaker:N|>` turns, `[direction]` + free-native `[bracket]` tags
- **Paired `<tag></tag>` FORBIDDEN** — dead on the free tier (our prep
  auto-converts, but don't author them: `<whisper>x</whisper>` → `[whispering] x`)

**readout .read.txt** (`NN-<slug>.read.txt`): verbatim book text, no speaker
tags (single narrator resolves from channel lock), footnotes dropped.

## What influence returns (damn reads)

- Bank clip: `{name, voice, backend, chars, credits_quoted, url, pilot?}`
- Master receipt: per-segment `{i, speaker, voice_id, chars}` + source path
- Cast sheets: `studio/channels/<channel>/casts/<collection>.cast.json`
  (briefs + candidates + auditions + contrast notes)
- Voice locks: channel record chairs (fish_id + reason + timestamp)

## Shared IDs

- Video: `FF-<season>-<collection-dir>` (e.g. `FF-S2-folklore-kwaidan-part-1`)
- Cast sheet: `studio/channels/<channel>/casts/<collection>.cast.json`
- Channel record: `studio/channels/<slug>.json` (thesis in same repo)
- Video item: bgraph `registry/content/items/<video_id>.json` (44 live)

## Ownership (no stepping)

damn: scripts, routines, pilots queue + verdicts, gate/poison/normalize.
influence: renders, voice locks + seeds, channel/series records, video
items, R2 audio. bgraph: identity + video registry (validated exports).

## Change protocol

1. Propose in the other lane's chat (or owner relays).
2. Both lanes' tests green (their `fish/validate.py`, our `pytest`).
3. Version bump (`content-contract.v2`) — old readers keep working.
