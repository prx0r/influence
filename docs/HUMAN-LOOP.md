# Human-in-the-loop — the per-channel runbook (2026-10-14)

Automation does everything except taste. This doc lists every point
where a human decides, exactly what they see/hear, and what happens next.
If a step isn't listed here, no human is needed.

## The loop per channel

```
onboard channel → cast voices → snippet → full pilot → titles/thumb
→ ship → verdict → next (rinse per series)
```

## Checkpoint 1 — lock the narrator (once per channel)

- **You see:** casting view, 5 voice cards with playable samples + reasons
  (tags, prior uses, your taste anchors cited).
- **You hear:** each card's library sample + one-click "hear our line ($0)"
  rendering your actual script line in that voice.
- **You do:** pick one, write one-line why → lock. Reason trains proposals.
- **Then:** seed recompiles, narrator propagates to all 3 series as default.

## Checkpoint 2 — confirm each character voice (per role, per book)

- **You see (NEW):** on the channel entity, one task per open chair:
  `Cast yuki — confirm the voice`, with WHO they are — gender/age/role
  plus an actual sample line from the books, e.g.
  Yuki (female/young): *"Tell me about her... Where did you see her?"*
- **You hear:** same 5-card drill, samples are their real lines.
- **You do:** lock with reason. Open chairs stay UNKNOWN (progress bar
  honest); locked flip READY.
- **Then:** duel rosters resolve, batch renders use locked voices.

## Checkpoint 3 — snippet review (per pilot)

- **You hear:** first chunk rendered $0, inline player, plus prep score
  (before→after), flags, credit cost if billed.
- **You do:** approve → full render runs; or send back with a note
  ("older, slower") → pi recasts.
- **Then:** master lands in bank with receipt (segments × voices).

## Checkpoint 4 — titles + thumbnail (per video)

- **You see:** 3 title candidates from the recipe + tale metadata;
  thumbnail still (art + ≤3-word serif + gold rule).
- **You do:** pick one of each (or edit inline in channel config).
- **Then:** upload package assembles (unlisted-first; public flip is yours).

## Checkpoint 5 — verdict (per video, ~30 days later)

- **You see:** CTR/retention vs channel baseline, Jev score + format rank.
- **You do:** continue (unlocks etch chain) or kill (logged in pilots.md).
- **Then:** winners get covers/full art; losers teach the ranker.

## What the human NEVER does

Pick models, write prompts, normalize text, concat audio, upload files,
compute quotes, track receipts — automation owns all of it. Human time
per video after narrator lock: ~10 minutes (voices + snippet + titles).

## Rules braided in

0 credits ever (kill-switch) · verbatim P0 · one voice per project ·
differentiation (no shared voices) · every lock carries its reason.
