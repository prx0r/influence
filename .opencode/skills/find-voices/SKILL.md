---
name: find-voices
description: Hunt Fish Audio voices by archetype using the Fish MCP. Use ONLY when casting, finding, verifying, or locking voices for channels, chairs, or roles (folk-and-fable, sleep, damn runbooks, studio casting).
---

# Find Voices

Hunt voices on Fish Audio through the MCP. Metadata proposes, ears dispose —
never lock a voice the owner hasn't approved, and never render audio to
"check" a voice unless the owner explicitly says render.

## Tool order (matters)

1. **Known ID? Use `get_voice`, never `search`.** `search_voices` will not
   find a voice by its ID string, and direct REST lookup 404s on library
   voices. `get_voice(voice_id)` returns title, tags, sample URL, uses,
   likes, description. This was learned the hard way — twice.
2. **Unknown? Search wide, not deep.** Brief-worded queries retrieve
   ~15-tag lookalikes. Always pair narrow brief queries with a popularity
   sweep: `female narration storytelling`, `male narration storytelling`,
   `young conversational voice`, `calm sleep narration`.
3. **page_size caps at 20.** 25+ silently returns zero results. Breadth
   comes from more queries, never a bigger page.

## Think shelf, not adjectives (the owner's core lesson)

Tag-literal matching pulls the wrong genre. `whisper + breathy + female`
retrieves the sensual shelf (Seductive Whisper, Moan) — wrong for a snow
spirit. The right query is the archetype's shelf:

| Want | Search the shelf of | Veto the shelf of |
|---|---|---|
| frost (Yuki) | witch, dark, mysterious, commanding, dramatic | sensual, intimate, seductive |
| old storyteller | nostalgic narration, documentary, warm deep | announcer, energetic, bright |
| young female | friendly conversational, character-voice | sleep-whisper (wrong energy) |
| sleep narrator | calm, slow, measured, low, sleep-fit measured | anything high/fast/bright |

Role split (owner rule): narrators carry long passages warmly — prefer
`narration` voices. Characters are persona over carrier — prefer
`character-voice` tagged voices, which reads truer in dialogue even when
the name is less obvious. Never cast a narrator-typed voice as a
character just because its tags overlap; never cast sparkle-energy as
sleep-whisper.

Archetype beats tags. A Witch (dark/mysterious/commanding) is frost;
a whisper-model with identical calm/soft tags is not. When a pick
contradicts the tags, trust the pick and record why.

## Scoring (what the engine weighs)

`channel_onboard.propose` scores: theory fit 5, taste overlap 4, affect 2,
anchor cross-taste 2, fame 1 + buzz 2 + language 1. Fame is log-capped,
buzz is like-rate (trending outranks famous). Quality floor: skip
<200 uses unless owner-backed (anchor/incumbent bypass). Dedupe re-uploads
by normalized name, keep highest-use copy.

## Owner picks are training data

Every owner pick goes to `studio/voice-registry.json` under `tops` with:
`voice_id, name, status (owner-top / owner-top-locked / owner-reference),
reason, tags, sample, task_count`. Statuses:
- `owner-top-locked` — THE voice for a lane, overrides all slates.
- `owner-top` — house default, forks per project (damn: one narrator per
  project, never shared).
- `owner-reference` — taste reference only (e.g. bright kid/teen energy
  the owner likes but that must NOT leak into sleep slates).
Mirror the table in `damn/voices/registry.md` (Owner tops section).

## Tag schema (over-tag every voice: ~15 fields)

Every narrator/chair/collection carries `tags`: gender, gender_conf
(high/med/low — null when unsure, a wrong lock is worse than none), age,
era, archetype, shelf, energy, register, texture[], presence, pace,
warmth, voice_words[], truth (one-line lore: who this voice IS), vetoes[].
The engine feeds archetype/shelf/era/voice_words/texture/truth/presence/pace
into search keywords, enforces gender (anchors/incumbent bypass), and
penalizes veto hits −3 (cap −6). Thesis collections hold per-video tags;
channel chairs hold per-chair tags; `studio/voice-registry.json` holds
owner tops that override everything.

## Present, don't assign

Return slates of 3–5 with name, ID prefix, score, uses, one-line why, and a
playable sample each (Fish sample URL or `$0` audition clip in the voice
bank). Samples play inline in the studio Voices tab (click ▶). The owner
ear-checks and picks. A unilateral assignment (even a good one) is a bug.

## Render path (free only)

CLEAN VOICE DOCTRINE (owner law): voices render exactly as they are — no
pace/prosody edits (channel pace is 1.0 everywhere), no expression or
volume tweaks, no bed, no SFX, concat-copy masters. The studio sends
neutral knobs by default; explicit owner direction ("slower") still works
because that is a choice, not processing.

## Grade before render (ttslop)

`pipeline/ttslop.py <file>` — READY / NEEDS_WORK / BLOCKED with four parts
(readiness, direction coverage, attribution, hiccups) plus per-line matches
with fixes. Attribution is excused for verbatim readouts (the narrator
carries all dialogue by design). Never render below READY.

`CREDIT_SPEND_ENABLED` is unset: paid Drama/grant paths fail closed.
Render via `speak_free` / `sleep_studio.render_pilot` (model
`s2.1-pro-free`, $0, 0 credits). Locked channel chairs (`fish_id` in
`studio/channels/<slug>.json`) override drama-file stand-ins, so locking
the record re-points every render. Prep gate ≥70 + damn gate + poison run
per segment; chunks must fit 15000 bytes. No master without all speakers
cast — a missing chair fails loudly, never silently.
