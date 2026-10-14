# Handover — pack voice briefs + ranking honesty (2026-10-14, living doc)

For the next agent. Read AGENTS.md rules, then HANDOVER-CASTING.md (engine),
then this file (current state), then the files below.

## What this batch did

`pipeline/pack_cast.py` predicts the optimal Fish voice + full voice profile
for every characters pack (21 freaks): pack fields (persona, modulators,
motivations, vibe, archetype) → direction string → archetype classify +
affect estimate → `propose()` top-N → `studio/voice-profiles/<pack>.json`
(profile + archetype + affect + picks with samples/reasons).

## Ranking lessons (paid for, keep them)

1. **Popularity drowns taste.** `log10(uses)` capped at 10 let one mega-voice
   top all 21 packs. Now capped at 4 (`channel_onboard.py` pop line) —
   proof of life, not the decision.
2. **Tag stuffing drowns precision.** A 30-tag voice matches every query.
   Overlap now discounted by tag count (`8/max(8, len(tags))`).
3. **Anchors always survive the cut** (marked [LOVED]) + incumbent included
   for comparison. Owner taste is never paged out.
4. **BT needs ~20 pairs/function** before fitted weights beat priors.
   Until then hand weights + anchors + archetype carry ranking.

## Open threads (priority order)

1. Verify batch-3 briefs actually diversify tops (this run). If one voice
   still sweeps, next suspect: anchor overlap double-counting.
2. Owner's 3 F&F picks (narrator/yuki/minokichi) — everything trains on them.
3. `propose()` for pack direction uses folk-and-fable channel pitch as
   query noise — acceptable, flag if comedy packs get sleepy slates.
4. bgraph2 has no remote — channel seeds pile local.
5. Fal provider live but spend-gated (needs FAL_SPEND_ENABLED + grant).

## Files that matter (fresh agent reading list)

- `pipeline/pack_cast.py` — batch entry (this work)
- `dash/channel_onboard.py` — propose/lock/react/love/anchor_prompt (ranking lives here)
- `pipeline/ensemble_cast.py` — archetypes, affect, pitch bands, opposition
- `pipeline/bt_fit.py` + `pipeline/taste_profile.py` — BT fit, weights, pairs, uncertainty picker
- `pipeline/voice_acoustics.py` + `pipeline/voice_judge.py` — measured (not tag) truth
- `studio/voice-profiles/` — per-pack briefs (this batch's output)
- `studio/voice-anchors.json` — owner taste anchors (never delete)
- `studio/taste-profile.json` + `studio/taste-pairs.jsonl` — compiled weights + pairs
- `/root/characters/freaks/*/character.json` — source profiles
- `/root/characters/audition/voicelab/` — domains, stencils, MARY model, ab-prompts

## Never do

Spend credits (kill-switch). Invent voice IDs. Lock without a human reason.
Delete anchors, pairs, or seeds. Store secrets outside vault.

## Update — character profiles in casting UI (2026-10-14)

Casting grids (console onboard + studio Voices tab) now open with the full
character profile: mentions, dialogue count, gender/age/role, voice query,
actual book sample lines, ensemble brief, pitch band. Narrator-type chairs
correctly show no profile (roles aren't people). Next: per-pack brief pages
(`studio/voice-profiles/`) linked from the grid.

## Update — ship mode: audition protocol + engine + assignments (2026-10-14)

Narrator is per-collection (Adrian demoted to candidate). Casting order:
narrator first (reference voice), characters tune against it (contrast +
relationships), ranks last. Objective audition protocol
(`pipeline/audition.py` + `/audition.html`): same passage from the graph's
own lines, fixed speed from archetype pace target, $0 free-tier takes in
the bank, take-fit outranks tag-score. Judge takes, not vendor samples.

Character engine (`pipeline/character_engine.py`): graph -> bioacoustic
band (size->pitch/formants, motivation->texture, arousal->tempo) ->
search -> listen (`pipeline/voice_listen.py`, numpy/ffmpeg, no librosa)
-> fit/13 -> render recipe (pace target / measured rate -> prosody.speed
on s2.1-pro-free) -> learn (ranks -> pairs -> BT, taste sits ON taste
layer only; theory needs no ballots). Their repo owns delivery truth
(modulators/MARY/VIBE); we map (`character_to_voice.py`) + cast sleep.

Casting lanes: `studio/voice-thesis/<slug>.json` (predictions+whys),
`studio/casting/<slug>.json` (per-chair recommendations, never locks),
`studio/voice-measurements.json` (listen cache), cali page (?character=),
audition page (?m=manifest). Law unchanged: no lock without human reason,
0 credits, free tier only.
