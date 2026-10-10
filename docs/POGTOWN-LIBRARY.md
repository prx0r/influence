# Pogtown as performance library + open analytics

> Pogtown stops being "a comedy channel" and becomes:
> 1. The library of every performance (canonical record).
> 2. The analytics commons (open-sourced findings + experiments).
> 3. The stage where validated characters perform.

---

## Library (canonical performance record)

Every performance stored with:

```json
{
  "performance_id": "perf_nolan_042",
  "character": "no-nose-nolan",
  "character_version": 18,
  "show": "giraffe-science-hour",
  "episode": 12,
  "role": "guest",
  "jokeblocks": ["FALSE_EXPERTISE", "MISINTERPRETED_SUCCESS"],
  "hypothesis_id": "hyp_superiority_03",
  "script_hash": "sha256:...",
  "render_version": "v4",
  "youtube_id": "...",
  "aired_at": "...",
  "metrics_24h": {},
  "metrics_7d": {}
}
```

Lives in Pogtown repo (their authority). Influence reads for analytics +
graduation evidence. Same boundary as catalog packs: truth vs projection.

## Analytics commons (open source)

Publish, per show and per character (anonymized where needed):

- Episode metrics (views, retention, shares) at comparable ages
- Hypothesis outcomes (retained / revised / rejected + evidence)
- Mechanism weights (which JokeBlocks work in which contexts)
- Format findings (hook shapes, duration bands, posting times)
- Null results too (failed experiments are findings)

This is the comedy-science dataset. Open-sourcing it compounds:
outside researchers validate methods, creators learn, the field grows,
Pogtown becomes the reference corpus.

## Show validation ladder

```
pilot (3 episodes) → format metrics pass? → season (12) → hit?
→ spinoff/guest slots for tested characters → franchise
```

A show is a validated format when: retention floor held 3/3 pilots,
hook variance < threshold, production cost stable. Then characters
audition *within* the format — validated stage, variable talent.
