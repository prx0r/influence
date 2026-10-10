# Endgame vision: the autonomous creative factory (OddHobb × Pogtown × FinalBuilds2)

> Saved 2026-10-10 from research brief. The strongest endgame for the projects:
> an experimental system that discovers, generates, builds, publishes,
> measures, learns which creative *mechanisms* work, and reinvests.
> Keep Jev; no Unsloth fine-tuning for now.

## The loop

1. Discover unexplored product ideas, jokes, characters, audience interests.
2. Generate competing creative approaches.
3. Build the actual product, video, or advertisement.
4. Publish authorised experiments.
5. Measure real human behaviour.
6. Learn which underlying creative mechanisms work.
7. Reinvest into subsequent experiments.

Critical distinction: learn which creative *processes* work, not merely which outputs were popular.

## Key repos investigated

### mrsarac/ff-tracking (video production)
Procedural filmmaking: virtual camera films simulated terminal, glyph tracking,
lens effects, synchronised sound. Shared timeline of precise visual events drives
animation, focus, effects, sound. Translates to joke beats, reactions, cuts, cues.
Caveat: renderer targets macOS Metal; reuse architecture on Linux, don't assume portability.

### amathislab/terra (long-term)
Biomechanics → musculoskeletal sim → PPO control policies. Characters that move
with physical consistency. Requires specialist assets, GPU, restricted licences.
Research reference, not commercial pipeline.

### Priority table
| Repo | Unlocks | Priority |
|---|---|---|
| fframes | Fast Rust/SVG video rendering, agent inspection, snapshot tests, audio QC | P0 |
| YouTube Analytics MCP | Owner-channel analytics, retention, CTR, comparisons | P0 |
| yt-analytics-mcp | Smaller read-only adapter, good episode-age comparisons | P0 alternative |
| ff-unmute | Procedural soundtracks responding to audio measurements | P1 |
| FirstFrame | Progressive rendering, early approval, streamed previews, lineage | P1 |
| lipsync-engine | Streaming visemes, SVG/Canvas rendering | P1 |
| NVIDIA Kimodo | Controllable human motion from text/keyframes (Mar 2026) | P1 research |
| NVIDIA ARDY | Real-time text-directed character motion (Jul 2026) | P1 research |
| ardy2bvh | ARDY motion → BVH/FBX for Blender/Unity/Unreal | P1 research |
| MotionMind | Video → 3D motion → rigged avatar | Experimental |
| Agentic Video Editor | End-to-end editing reference architecture | Study |
| Meta SPIDER | Physics-informed motion transfer (noncommercial licence) | Research |

### Fused opportunity
Jev chooses what to make → creative agents write → specialised renderers produce
→ verified analytics inform next. Key engines: fframes (testable renders),
ARDY (actionable motion), FirstFrame (early approval).

## FinalBuilds2 assessment

Already has: idea research + scoring, autonomous worktree builders, independent
verification + promotion, append-only event/lineage graph, deterministic
experiment assignment, process-to-outcome attribution, hypothesis evolution
policy, creative production + distribution adapters.

Key files: `src/experiments/engine.js` (control/treatment), `src/analytics/
process-attribution.js` (observational vs causal), `docs/HYPOTHESIS-EVOLUTION-
POLICY.md` (promote on out-of-sample performance + calibration + evidence).

To integrate: closed-loop audience optimisation needs validation.
To expand: unit of work beyond software → products, campaigns, episodes,
performances. To validate: closed-loop audience optimisation.

## One OS, two factories

- **FinalBuilds2**: research, hypotheses, lineage, experiments, allocation.
- **Jev + qprivately**: decisions, verified gates, execution grants, receipts.
- **OddHobb (commercial factory)**: demand → design → mesh/print verify → pack → listing → campaigns → sales.
- **Pogtown (creative factory)**: trend research → JokeBlocks → characters → scripts → animation → YouTube → audience response.
- **Shared ledger**: results → comparisons → hypothesis updates → next experiments.

Strict domain boundaries: FinalBuilds2 owns experiment lifecycle; Influence owns
brand marketing/distribution; Pogpet owns product truth/artifacts/fulfilment;
Freaktown/Pogtown own characters/JokeBlocks/episodes; qprivately owns proofs;
Jev decides, never the source of truth.

## Pogtown as humour science (prototype first)

Every episode = formal experiment with declared humour theory. Example NOLAN-007:
hypothesis (laughter-as-competence vs recognised incompetence) → controlled
variants A (self-aware, control) / B (misinterpreted success, treatment) →
constant character/voice/duration/setting → measure retention/rewatches/shares
→ update hypothesis (retain/revise/reject).

Goal: learn mechanisms ("overconfidence after failure works when sincere, not
when arrogant"), not just "Nolan got 25k views." Feed back into generation.

YouTube caveats: 2-3 day reporting lag; no true randomised A/B (recommendation
confounds); treat as noisy observational. Pogtown's own Pog button enables
controlled experiments later. Two environments: YouTube (discovery) + Pogtown
(controlled).

## Ship order (narrow loop first)

1. Pogtown episode contract (character version, JokeBlock IDs, hypothesis, script, render version, YouTube ID).
2. fframes rendering adapter (one short from structured timeline + snapshots + audio QC).
3. Review canvas (preview/approve/reject/request-changes).
4. YouTube analytics ingestion (comparable-age snapshots + availability flags).
5. FinalBuilds2 experiment adapter (episode → hypothesis → arm → lineage → outcome).
6. Jev decision routing (next experiment under explicit budget, log alternatives).
7. Closed-loop proof (several episodes → evidence-informed creative brief).

Parallel OddHobb loop (smaller): pack → listing → campaign creative →
impressions/clicks/orders → next creative decision. Shared infra, independent
generators and rewards.

## Long-term asset

Evidence-backed library of creative mechanisms, characters, product designs,
experiments — generating, testing, learning, improving. Plus the bridge:
Pogtown characters with demonstrated appeal → OddHobb authorised merchandise.

Next move: small integration across FinalBuilds2 + Freaktown + fframes +
YouTube Analytics. Keep Jev, preserve verification boundaries, prove one
complete feedback cycle before more infrastructure.
