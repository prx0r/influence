# Influence studio — docs index (2026-10-14, living)

Start here. Each doc is one concern; cross-links at the bottom of each.

## The system in 30 seconds

16 YouTube channels. Scripts come from damn, strategy from sleepintel,
identity from bgraph, execution here, voices from Fish. $0 default,
kill-switch on spend. Human decides taste; automation does everything else.

## Read in order

1. **CHANNEL-SYSTEM.md** — the map: repos × roles, channel→series→videos
   hierarchy, format tags, flows, market grounding, doors.
2. **ONBOARDING.md** — full channel onboarding: intake → validation →
   voices → vibe/style/theory → binding → pilot. Pi's lead checklist included.
3. **HUMAN-LOOP.md** — the 5 human checkpoints: what you see/hear/do at
   each, ~10 min/video after narrator lock.
4. **CONTENT-CONTRACT.md** — damn ⇄ influence formats (drama.txt headers,
   readout layout, shared IDs, ownership, change protocol). Machine twin:
   `studio/content-contract.json`.
5. **MEDIA-PIPELINE.md** — voice → titles → thumbs → images → sleepdraw
   assembly → R2 → upload. Per-stage cost/gate/status. fal needs key + approval.
6. **ASSETS.md** — where every artifact lives + lifecycle + final-mux spec
   + FableCut verdict.

## Live surfaces

- Studio: https://youtube.agentcom.org (channels as entities)
- Console: https://youtube.agentcom.org/classic
- Legacy commerce dash: https://agentcom.org (do not touch for studio work)

## Key files (source of truth, not docs)

- `studio/channels/<slug>.json` — channel record (thesis → voices → formats)
- `studio/taxonomy.json` — format/engine/status tags
- `studio/voice-anchors.json` — owner taste anchors weighting proposals
- `pipeline/` — tts_text, audio_flow, jev, cast/ensemble, thumb, yt_compliance
- `dash/` — server, MCP tools, pi chat, studio UI, onboarding, grants

## Laws (AGENTS.md 1–13, binding)

0 credits ever · verbatim P0 · one voice per project · free tier default ·
receipts always · secrets never in tree · YT dash is THE dash.
