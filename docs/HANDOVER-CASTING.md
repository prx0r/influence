# Handover — voice casting + taste engine (2026-10-14, living doc)

For the next agent (human or model) continuing this lane. Read AGENTS.md
rules first, then this file, then the code it names.

## What exists and where

- **Casting engine** (`dash/channel_onboard.py`): `propose()` ranks 5 from
  the Fish catalogue by vibe queries + tag overlap + taste weights +
  function fit + affect match + acoustics + popularity, minus sibling
  penalty. Loved voices + incumbent always survive the cut. `lock()` writes
  voice + reason + history, recompiles seed. `react()`/`react_thumb()`
  store ticks/notes/dismissals. `love()` anchors new voices with your words.
  `anchor_prompt()` compiles anchors into voice-design instructions.
- **Taste profile** (`pipeline/taste_profile.py` → `studio/taste-profile.json`):
  locks(3)/anchors(2)/likes(1)/dismissed(-2) compile to 85 weights;
  pairwise rankings fit per-function weights (`whisper`, `narration`…);
  BT mini-LoRe over pairs (`bt_refit`, unified hot..cold verdicts);
  sleep-lane + visual-lane linkage; uncertainty picker (`next_character`).
- **Archetypes** (`pipeline/ensemble_cast.py`): 10 research-grounded voice
  archetypes (overlord/imp/hero/mentor/fae/crone/beast/trickster/innocent/
  elder) with pitch/pace/projection/delivery + MARY-compatible affect dims;
  `classify_archetype()` feeds propose(); `oppose_band()` places villains
  opposite heroes. Rule: research gets close (objective), owner taste
  narrows within (subjective).
- **Acoustics** (`pipeline/voice_acoustics.py` + `studio/voice-acoustics.json`):
  measured F0/energy/density per loved voice; lie detector vs Fish tags;
  sleep-fit cited in ranking (±1.5, never veto — demo samples overstate).
- **Renders** (`pipeline/audio_flow.py` speak_free + `providers/fish_rest.py`
  s2.1-pro-free, knobs speed/volume/temp): $0, no grants. Credits paths stay
  grant-gated + kill-switched (`CREDIT_SPEND_ENABLED` unset).
- **Studio UI** (index.html onboard view + yt.html Voices tab): grid cards,
  samples, ticks, rank inputs, hear-our-line, lock, design-new ($0.01,
  confirm-first). `/cali.html`: uncertainty-rank loop page.
- **Channels** (`studio/channels/*.json`): 16 records + seeds + briefs +
  dramatis + casts + taste files. F&F narrator currently Adrian (Calm Sleep
  + old-man-bible challenging — owner decides).

## Open threads (priority order)

1. Owner's 3 pending picks (F&F narrator/yuki/minokichi) — everything else waits on taste.
2. BT fit needs ~20 pairs per function before it beats hand weights.
3. "King"-style smeared names in dramatis (role, not person) — per-book scoping.
4. Demo-sample variance overstates sleep risk — judge takes, not samples.
5. bgraph2 has no remote — seeds pile up local until `prx0r/bgraph2` exists.

## Never do

Spend credits. Invent voice IDs/prices. Lock without a human reason.
Re-record without new framing. Store secrets outside vault.
