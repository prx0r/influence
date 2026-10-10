# Closed-Loop Content Learning — Jev judges, stats decide, bandit allocates

> 2026-10-10. Generate → publish → measure → Jev classifies → stats validate →
> weights update → next batch. Jev makes typed judgments about content. The
> statistical learner calculates which judgments correlate with outcomes.
> A bandit allocates the next batch. Humans approve everything that publishes.

---

## The loop

```
1. GENERATE   10 candidate scripts/posts (existing pipelines)
2. JUDGE      Jev assigns typed attributes (hook, structure, emotion…)
3. PREDICT    expected reward per candidate from current weights
4. SELECT     bandit picks next experiment (70/20/10 → Thompson later)
5. RENDER+PUBLISH  existing factories + human_confirm gate
6. MEASURE    24h + 7d snapshots (AgentTube pattern)
7. UPDATE     Spearman + BH + power gates (jev-writer methodology)
8. FEED       winning patterns → next generation brief
9. REPEAT
```

---

## Why build, not adopt

| Candidate | Verdict | Reason |
|---|---|---|
| jev-writer | ADAPT (port) | Stats + rubric discipline exactly right, but Node.js. Port is trivial (stdlib). |
| linkedin-viral-meter | MINE | Draft-scoring UX good; stats weaker (no date confound, no BH, p≫n). |
| AgentTube | MINE | 24h/7d snapshots + approved-only injection + experiment math. Node/Express, extract algorithms. |
| jevcut | ADAPT (vendor) | Already Python + our exact Jev setup. Closest to direct reuse. |
| reelql | MINE patterns | Third-party service, can't self-host. Minimal-state + 5-question pattern. |
| learn_to_pick | WRAP later | Small, delayed-feedback API fits. Not needed until we have volume. |
| mabwiser / river | PIP later | Thompson/UCB + online ML when data justifies it. Start with 70/20/10. |

**We have what none of them do:** pinned Jev model, QP receipts, human approval gates, SQLite, audit ledger, multi-brand accounts, supplier entities. The loop plugs into OUR runtime.

---

## Data model

```sql
-- content items (what we published)
CREATE TABLE IF NOT EXISTS content_items (
  id INTEGER PRIMARY KEY,
  at TEXT NOT NULL,                  -- published timestamp
  channel TEXT NOT NULL,             -- x | youtube | tiktok | instagram
  account TEXT NOT NULL,             -- @oddhobb
  brand_slug TEXT DEFAULT 'oddhobb',
  kind TEXT,                         -- post | video | short | pin
  title TEXT DEFAULT '',
  body TEXT DEFAULT '',              -- script / post text
  hook_text TEXT DEFAULT '',          -- first 2s / first line
  external_id TEXT,                  -- tweet_id, video_id
  url TEXT DEFAULT '',
  action_id INTEGER,                 -- links to actions ledger
  receipt_id TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

-- Jev features (typed judgments per item)
CREATE TABLE IF NOT EXISTS content_features (
  id INTEGER PRIMARY KEY,
  item_id INTEGER,
  pack_version TEXT NOT NULL,        -- rubric pack id + version
  question_id TEXT NOT NULL,         -- hook_question, payoff_warmth...
  qtype TEXT NOT NULL,               -- score | bool | choice
  value REAL,                        -- normalized 0-1 (score/(L-1), P(true), P(opt))
  choice_opt TEXT,                   -- winning option for choice Qs
  agreement REAL,                    -- inter-rep agreement
  confidence REAL,
  reps INTEGER DEFAULT 5,
  rated_at TEXT DEFAULT (datetime('now')),
  UNIQUE(item_id, pack_version, question_id),
  FOREIGN KEY (item_id) REFERENCES content_items(id)
);

-- performance snapshots (24h + 7d, AgentTube pattern)
CREATE TABLE IF NOT EXISTS performance_snapshots (
  id INTEGER PRIMARY KEY,
  item_id INTEGER,
  window TEXT NOT NULL,              -- 24h | 7d
  views INTEGER DEFAULT 0,
  likes INTEGER DEFAULT 0,
  shares INTEGER DEFAULT 0,
  comments INTEGER DEFAULT 0,
  saves INTEGER DEFAULT 0,
  clicks INTEGER DEFAULT 0,
  orders INTEGER DEFAULT 0,
  followers_at_post INTEGER DEFAULT 0,
  reach_rate REAL,                   -- views / followers_at_post
  conversion_rate REAL,              -- engagements / views
  simulated INTEGER DEFAULT 0,       -- 1 = exclude from learning
  taken_at TEXT DEFAULT (datetime('now')),
  UNIQUE(item_id, window),
  FOREIGN KEY (item_id) REFERENCES content_items(id)
);

-- strategy weights (what we've learned)
CREATE TABLE IF NOT EXISTS strategy_weights (
  id INTEGER PRIMARY KEY,
  brand_slug TEXT DEFAULT 'oddhobb',
  channel TEXT DEFAULT 'all',
  pack_version TEXT NOT NULL,
  question_id TEXT NOT NULL,
  dim TEXT NOT NULL,                 -- hook_question, payoff_warmth...
  direction TEXT,                    -- higher | lower | neutral
  rho REAL,                          -- partial Spearman (date-controlled)
  p_value REAL,
  bh_pass INTEGER DEFAULT 0,         -- survived Benjamini-Hochberg
  n INTEGER,                         -- sample size
  power TEXT,                        -- strong | weak | descriptive
  effect_size REAL,                  -- Cohen's d or median lift
  weight REAL DEFAULT 0,             -- allocation weight (|rho| if validated)
  updated_at TEXT DEFAULT (datetime('now')),
  UNIQUE(brand_slug, channel, pack_version, question_id)
);
```

---

## Rubric packs (versioned, Jev-typed)

Packs live in `pipeline/learn/packs/*.json`. Format (from jev-writer, adapted):

```json
{
  "id": "video-script",
  "version": "v1",
  "stateFields": ["hook_text", "script_body", "caption"],
  "outcomes": {
    "reach_rate": "views / followers_at_post",
    "conversion_rate": "(saves+shares+clicks) / views"
  },
  "questions": [
    {
      "id": "hook_question",
      "type": "bool",
      "tier": "primary",
      "question": "The hook is phrased as a direct question to the viewer.",
      "note": "Refers to {hook_text}."
    },
    {
      "id": "hook_surprise",
      "type": "score",
      "tier": "primary",
      "levels": 5,
      "question": "How surprising is the opening?",
      "criteria": ["expected opening", "mild twist", "genuine surprise", "shocking", "unbelievable"]
    },
    {
      "id": "payoff_warmth",
      "type": "score",
      "tier": "primary",
      "levels": 5,
      "question": "How warm is the emotional payoff?",
      "criteria": ["cold", "neutral", "mildly warm", "heartwarming", "tearjerker"]
    }
  ],
  "directions": {
    "hook_question": "higher",
    "hook_surprise": "higher",
    "payoff_warmth": "higher"
  }
}
```

**Rules (from jev-writer, non-negotiable):**
- 12–18 questions max (keep family small for BH)
- `score` 2–10 ordered levels, `bool` → P(true), `choice` needs `none_of_these` escape
- 5 reps per item, mean + sd
- Never ask Jev to count (code features: duration, words, hashtags)
- Wording is load-bearing — edits = version bump + re-rate
- Code-counted features compete equally (duration, word count, emoji, hashtags)

---

## Statistical methodology (jev-writer port)

```
Per outcome (reach_rate, conversion_rate separately):
1. Power gate:  n<25 → descriptive only (refuse correlations)
                25-60 → weak (report criticalR, MDE, E[FP])
                60+ → full report
2. Spearman rank (Jev magnitudes are ordinal, no interpolation)
3. Date confound: partialSpearman(values, outcome, date)
4. BH correction on date-controlled p, per-outcome family
5. Report: rho, p, BH pass/fail, n, power, effect size, CI
6. Weights: |rho| for BH-passed dims, 0 otherwise
```

No logistic regression until n>200 (p≫n problem in viral-meter).
No claims without power gate passing.

---

## Selection policy (start simple, grow into bandits)

```
Phase 1 (now, n<50):  70/20/10
  70% proven formats (highest weights)
  20% promising variations (positive but unvalidated)
  10% new experiments (unrated dims)

Phase 2 (n>100):  Thompson Sampling via mabwiser (pip install)
Phase 3 (n>500):  learn_to_pick with delayed rewards
```

---

## Measurement windows (AgentTube pattern)

```
24h snapshot:  ageHours >= 24, first reliable read
7d snapshot:   ageHours >= 168
Exclude:       simulated=1 (never learn from fake data)
Baselines:     median of prior reliable snapshots, same channel
Min samples:   n>=2 per group for recommendations
Approval:      findings default pending, human approves before
               they influence future runs (approved-only injection)
```

---

## Generation brief (what the loop outputs)

```json
{
  "brief_id": "brief-2026-10-15",
  "brand": "oddhobb",
  "channel": "tiktok",
  "validated_patterns": [
    {"dim": "hook_question", "direction": "higher", "rho": 0.42, "n": 67},
    {"dim": "payoff_warmth", "direction": "higher", "rho": 0.35, "n": 67}
  ],
  "allocation": {"proven": 7, "promising": 2, "experiment": 1},
  "constraints": ["hook must be a question", "payoff must score >=4"],
  "approved_by": "human",
  "approved_at": "..."
}
```

The content factory reads the brief. Human approves the brief. Then generation runs.

---

## Rewards by channel

| Channel | Primary reward | Supporting signals |
|---|---|---|
| OddHobb social | Attributable profit/orders | Product clicks, saves, engaged views |
| Pogtown | Sustained engagement | Completion, shares, Pog votes, returning viewers |
| YouTube | Watch-time + growth | Retention, CTR, returning viewers |
| Etsy (from social) | Orders | Click-through from pins/posts |

---

## Implementation order

| # | Slice | Status |
|---|---|---|
| 1 | Tables (items/features/snapshots/weights) | → build now |
| 2 | Rubric packs (video-script v1, product-post v1) | → build now |
| 3 | Jev rating runner (5 reps, pack_version pinned) | → build now |
| 4 | YouTube snapshot puller (24h/7d) | extend analytics.py |
| 5 | Stats module (Spearman/BH/power, stdlib) | → build now |
| 6 | Brief generator (weights → constraints) | after first data |
| 7 | jevcut vendor (clipping) | after loop works |
| 8 | Bandits (mabwiser/learn_to_pick) | n>100 |
