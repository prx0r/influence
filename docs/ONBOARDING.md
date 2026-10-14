# Channel onboarding — the full flow (2026-10-14)

FableCut note: yes, it's in the repo (`/root/fablecut`, v1.11.0, MCP +
REST). Evaluated as the future edit-decision layer (project.json
timelines instead of opaque ffmpeg). Not running yet — adopted when human
timeline tweaks become the bottleneck. This doc assumes direct assembly.

## What arrives (from the scripts lane)

1. Pilot script (`damn/projects/<house>/pilots/NN-<slug>.drama.txt`)
2. Materials bundle: source book refs, art direction notes, SFX spots,
   tale metadata (tradition, PD provenance URLs)
3. Routines 01–07 status + pilots.md verdict slot

 intake checklist: header chairs with voice IDs? speaker tags balanced?
 paired `<tag></tag>` absent (forbidden — prep converts, but flag back)?
 2-minute shape (166–216 words)? If any fail, send back with reasons —
 never fix scripts silently (their lane owns the words).

## Stage 1 — validate TTS-readiness (automation, $0)

Run `prep` (clean → normalize → chunk → score). Gate: score_after ≥ 70,
zero surviving digits/URLs, frontmatter dropped, paired tags converted.
Then damn `gate` (budget/junk/boilerplate/drama-balance/sleep-safety) +
`tts-poison` (20 checks). Read it as if a model will speak it cold:
every number spoken, every abbreviation expanded, every quote attributed
or flagged, no stage directions leaking into audio. Refusals carry the
exact flag list back to the scripts lane.

## Stage 2 — map voices with the voice engine (automation + human)

1. `cast_extract` the source book → dramatis (characters + profiles +
   voice queries). Evidence attached, nulls stay null.
2. `compose_cast` → briefs ("what should a tree sound like?" answered
   from role/size/age/function), pitch bands, contrast check.
3. `prepare_cast` → top-3 candidates per speaker + $0 audition each.
4. Anchors weight ranking (owner taste: Luna/Verity/SpongeBob/Darwin…);
   sibling locks excluded (differentiation law).
5. **Human:** listen, pick, one-line reason → lock. Seed recompiles.
   Narrator first (propagates to all series), then characters.

Voice-design engine (P0, $0.01/req, approval-gated): channel record →
instruction prompt → candidates → previews → lock. For chairs no library
voice fits. Never default — always an approved event.

## Stage 3 — channel vibe, style, theory, audience (human-led, pi-assisted)

Write into `studio/channels/<slug>.json` (config UI or pi dictation):
- **thesis** (1–2 lines: why this channel exists, what belief it tests)
- **audience** (who, age band, adjacent YouTube overlap, explicitly NOT who)
- **style** (accent hex, manner clause, visual grammar, shelf)
- **thumbnail** (type + rules; channel standard unless series overrides)
- **formats** (tagged from taxonomy: talefull/excerpt/mythcrossover/…)
- **cadence** (3x/week + flagship rule), **bed**, **pace**
- **theory note**: why this combination works (sleep grammar + persona
  firewall + ritual loop), 3–5 lines, falsifiable where possible.

Pi's job here: interview the human (one question at a time), draft each
field from answers + market intel (AvatarChannels: zero sleep competition,
persona gaps, 15–20min norms), read back for confirm, save via config
endpoint. Never invent audience data — "to confirm" beats guessing.

## Stage 4 — bind it into every generation (automation)

Once locked, the record drives all downstream calls without re-asking:
- audio: chair → locked fish_id; pace → prosody.speed; bed + ducking
- Studio imports: roster pre-filled from chairs (no re-casting)
- titles: recipe + tale metadata + format tag
- thumbnails: art frame + title + accent + rules
- video items: channel/series/voices/R2 path auto-filled
- verdicts: aggregated by format tag + series

Drift check (monthly or on complaint): re-run prep on 3 shipped scripts;
if score_after < 70 or voices drifted from locks, flag for review.

## Stage 5 — pilot with the human (the loop that never ends)

`HUMAN-LOOP.md` checkpoints: narrator lock → character confirms (with
book-quote tasks on the entity) → snippet → titles/thumb → verdict.
Human time per video after narrator lock: ~10 minutes.

## Done = channel is live when

Record complete (thesis/audience/sourcing/style/chairs locked/cadence) +
narrator ear-checked + 1 pilot master in bank + R2 + thumbnail + titles
picked + first unlisted package assembled. Then cadence runs unattended
except locks, picks, and verdicts.
