# Folk & Fable — channel pack (2026-10-14, autonomous build)

Status: pilot. Snippet rendered $0, in voice bank. Everything below is
reasoned from measured baselines, not vibes (sources at bottom).

## Snippet (listen first)
- `free-075104-01.mp3` (~90s, Adrian narrator, $0) — Yuki-Onna opening:
  Musashi woodcutters → ferry → snowstorm → ferryman's hut. Prep 87→100,
  title page auto-dropped. Play in dash Content tab → voice bank.
- Full opening = 2 chunks (~5k credits IF rendered on credits; $0 on free tier).

## Target audience
Adults 25–54 who use narrative to fall asleep: ex-podcast sleepers bored of
flat AI voices, folklore-curious (mythology YouTube overlap), second-screen
"rain video" graduates wanting story without stimulation. NOT kids content
(AI disclosure + not-made-for-kids at upload, per differentiation law).
Competitor proof: Historian Sleepy 214k subs (verified live via YT API
2026-10-14); Sleepy History Stories daily 2h+ cadence; tubeintel sleepiness
baselines rain 1.9 > facts 1.37 > place 1.11 — NARRATION + PLACE outranks
facts, so tales beat trivia for this shelf.

## Brand image
Avatar/banner candidate (no spend): `sleepdraw/assets/moon-lora1-flux-pencil.jpg`
— proven lora1 house art (kind moon, vast black). Cottage-glow variant for
banner: quote Nano Banana edit (~600cr) AFTER snippet ear-check passes.
Rule: one moon, one gold (`#D4A94E`), never character faces (faces wake people).

## Styling logic (why, not just what)
- Black canvas + white pencil + hearth-gold accent: sleep grammar (dark +
  one warm point). Accent `#9B7EDE` reserved for fae-title cards only.
- Fixed cast wording (sleepdraw bible): same moon, same hut, every tale —
  familiarity is the product; novelty is the tale, never the look.
- Voice: ONE narrator (Adrian, ear-checked) + tale-local chairs (Yuki
  whisper, Minokichi earnest). Locked IDs in `folk-and-fable.json`.
- Pace 0.85, bed music-box+rain+owl at 35% ducked 2dB. Silence between
  passages is content (blackout synced, easy mux precedent).

## Thumbnail type
Black field, single etched object (doorway/hut/moon), 3-word max title text
in warm serif, gold rule. NO faces, NO red arrows, NO shock type — CTR comes
from shelf recognition (same look = same promise), per umbrella verdict rule:
variety first, winners get etch-chain upgrades after 30-day retention data.

## Title type
`[Tradition] [Story] — Sleep Reading | [Duration]`: e.g.
"Japanese Folklore: Yuki-Onna — Sleep Reading | 1 Hour". Ritual description
(headphones + phone face-down) + chapters + PD provenance + playlist link.
6 fixed tags + 4 per-video. Pinned comment = next-episode hook (easy package).

## 5 launch videos (reasoned order)
1. **Yuki-Onna full (~12min, S2)** — queued pilot, Hearn PD, doorway art
   exists, cast locked. Reason: zero-competition depth (no big channel owns
   Kwaidan sleep), tests narrator + 2 chairs + SFX discipline at once.
2. **Snow Queen excerpt (~10min, S1)** — nostalgia surface (everyone knows
   the name, nobody has a sleep version). Reason: search demand + S1 entry
   point; excerpt first, 45min spec after retention verdict.
3. **Cyclops excerpt (~10min, S3)** — monster + trick, one SFX family.
   Reason: crossover bait for mythology-YouTube viewers (highest-value
   adjacent audience); tests whether S3 converts.
4. **Emperor's New Clothes (~15min, S1)** — Andersen, prepped 62→96 today.
   Reason: shortest path to a second S1 data point; same narrator, no new
   chairs — isolates story-vs-voice in the verdict.
5. **Baba Yaga (~15min, S2)** — zero-competition depth + hut visual reuses
   Yuki-Onna doorway grammar. Reason: if #1 works, #5 proves the S2 system
   repeats (system > video is the thesis being tested).

Verdict rule (damn, adopted): ship audio + black + 1 still → 30-day
CTR/retention → winner gets etch chain. Kill/continue in pilots.md, not vibes.

## Integration map (where everything lives now)
- damn `projects/folk-and-fable/` = runbook (routines 01–07, pilots queue)
- sleepintel engines/registry = strategy + engine contracts (E2-reading)
- bgraph brand branch = identity + R2 layout + upload method (unlisted-first)
- influence studio = execution (prep → snippet → grants → bank → receipts)
- this file + `folk-and-fable.json` = canonical channel record (style +
  chairs + cadence). Renderers read it; vaults reference it by hash.

## Sources
tubeintel baselines + competitor registry; YT Data API live check 2026-10-14;
easy docs/CHANNELS (upload package) + Bremen precedent; damn theses +
pilots; sleepintel ENGINES + hypotheses; powvid lora1 lock + vault pattern.
YT key: influence/.env (YOUTUBE_DATA_API_KEY, vault-sourced, 600, ignored).
