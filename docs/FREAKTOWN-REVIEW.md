# Freaktown review — what exists vs what the character endgame needs

> Reviewed prx0r/freaktown @4722b9f (cloned 2026-10-10, scratch copy removed).
> Scope: live show runtime. Verdict: 70% of the character side is real.

---

## Exists and working

| Endgame need | Freaktown reality |
|---|---|
| Character packs | `docs/CHARACTER_PACK.md` — folder = freak (character.json, avatar, voice, delivery) |
| Contract versioning | `contracts/*.v1.schema.json` frozen + golden fixtures + SDK tests |
| Delivery beats incl. callbacks | `delivery.v1` (setup/escalation/misdirect/punchline/tag/callback/closer) |
| Reply lineage (social world primitive) | `lineage.v1` (relation, parent/root IDs, depth) |
| Performance records + compiler | `performance.v1` + `backend/services/performance_compiler.py` + episodes routes |
| Live stage (events, SSE) | `apps/live`, episode-room worker, PartyRoom |
| Scoring from real data | Ella rubric from 225 Kill Tony sets |
| Cast with premises | 5 starters + 14 guests, Ella bible |

## Missing (the state layer)

| Endgame need | Status | Build |
|---|---|---|
| CharacterGraph versions | ❌ Facts are static lists | Add `version`, versioned `beliefs[]` (claim + committed_at + source_event) |
| Relationships graph | ❌ Lore in prose only | `relationships{}` per character pair, queryable |
| Public events log | ❌ No append-only claim log | Per-character JSONL (claim, date, channel, event ref) |
| Graduation state machine | ❌ No stages/thresholds | draft→…→public_persona (our goals system can track) |
| Interview state machine | ⚠️ Content exists, no runtime | Pending-callback queue + contradiction tracker |
| Scene director | ❌ No who-speaks-next | New `scene` object (shared context version) |
| Commercial policy | ❌ None per character | `commercial_policy` in entity (our side can hold this) |
| Analytics → weights | ❌ Records exist, no learning | Feed performance → our learn loop |

## Recommended build order (freaktown side)

1. **Character pack v2**: `version` + `beliefs[]` + `relationships{}` (all optional, backward compatible).
2. **Public events log**: append-only per character. What Influence reads before posting.
3. **Graduation thresholds**: metrics → stages (tracked as Influence goals).
4. Scene director, interview runtime, commercial policy — after 1-3.

## Boundary (frozen)

- Freaktown owns: canon, beliefs, relationships, lore, show runtime.
- Influence owns: public entities, channels, approvals, receipts, learning.
- Character packs live in freaktown repo. Influence reads pinned versions.
- Same boundary as catalog packs: truth vs projection.
