# Character entities — Nolan as the first non-brand entity

> How a graduated character becomes an Influence entity with subdomain,
> email, channels, and commercial policy. Same machinery as brands,
> different authority.

---

## Entity model (extends bgraph, no fork)

```json
{
  "entity_id": "no-nose-nolan",
  "kind": "character",
  "source": {
    "authority": "freaktown",
    "ref": "freaks/no-nose-nolan",
    "character_version": 18
  },
  "identity": {
    "display_name": "No-Nose Nolan",
    "domain": "nolan.pogtown.com",
    "email": "nolan@pogtown.com",
    "phone": "shared:+447822000802",
    "voice_policy": "character_graph"
  },
  "channels": {
    "youtube": {"handle": "@nonosenolan", "status": "prospect"},
    "instagram": {"handle": "@nonosenolan", "status": "prospect"},
    "x": {"handle": "@nonosenolan", "status": "prospect"},
    "tiktok": {"handle": "@nonosenolan", "status": "prospect"}
  },
  "commercial_policy": {
    "brand_deals": "human_approval",
    "merch": "allowed",
    "paid_posts": "human_approval"
  },
  "graduation": {
    "stage": "contestant",
    "evidence": [],
    "thresholds": "see GRADUATION.md"
  }
}
```

## Contact rules (decided)

| Contact | Rule | Nolan today |
|---|---|---|
| Subdomain | `{entity}.pogtown.com` on graduation to `recurring`+ | nolan.pogtown.com (reserve now) |
| Email | `{entity}@pogtown.com`, routed to studio inbox | nolan@pogtown.com |
| Phone | Shared studio number, entity tag on OTP routing | shared |
| Own domain | Only at `breakout`+ with audience evidence | no |
| Etsy shop | At `public_persona` with merch demand | no (yet) |

## Graduation stages + evidence thresholds

| Stage | Requires | Influence unlocks |
|---|---|---|
| `draft` | exists in Freaktown | nothing (Freaktown-only) |
| `contestant` | 1 performed set | entity row, no channels |
| `recurring` | 3 sets, positive Ella score trend | subdomain + email |
| `regular` | 5 sets, 1 catchphrase adoption | + 1 social channel (lowest-risk) |
| `breakout` | 10k views single piece OR 3 return requests | + all socials, podcast guest slots |
| `public_persona` | sustained 30d engagement + merch demand signal | + Etsy shop, brand deals, AR |

Evidence comes from performance records + analytics. Transitions are
proposed by the system, confirmed by human (graduation is a HumanAction).

## Voice resolution (frozen rule)

```
IF kind == character AND source.authority == freaktown:
    voice/style ← CharacterGraph ref @ character_version
    bgraph local voice/style IGNORED (fallback only on fetch failure)
ELSE:
    voice/style ← bgraph local (brands, existing behavior)
```

Influence never writes character canon. It reads a pinned version.
Version bumps are Freaktown events; Influence re-reads on next compile.

## Publicity gate (before every character post)

```
1. canonical?      (in CharacterGraph at pinned version?)
2. publicly established?  (in Public Graph, i.e. audiences saw it?)
3. safe to reveal?  (no unestablished lore, no future-arc spoilers?)
4. consistent?      (matches current character state + show bible?)
```

Fail any → draft blocked with reason → human or Freaktown resolves.
This is a machine pre-gate, before the human review task.

## Commercial policy enforcement

Grants carry `commercial_policy` constraints:
- `merch: allowed` → OddHobb merch pipeline auto-approved up to cap
- `brand_deals: human_approval` → always a task, contract attached
- `paid_posts: human_approval` → always a task with copy + fee
- Sponsor claims live in Influence (contract truth); Freaktown owns expression.
  qprivately: no deal outside an authorized contract.
