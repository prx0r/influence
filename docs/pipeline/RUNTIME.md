# Dashboard Runtime — audited actions, spend gates, receipts

> Design doc. The dash (agentcom.org) is the execution runtime for all
> brand actions: every API call, every publish, every cent. Built on
> qprivately (gates + receipts + grants), pogpet (provider router +
> ledgers), workerkit (campaign lifecycle), agentcom (campaign blueprints).
>
> **One sentence:** every action is a gated, granted, receipted, costed,
> auditable event — visible in one list, with money stopped at a human gate.

---

## What exists (don't rebuild)

| Piece | Where | State |
|---|---|---|
| Gates (content-addressed, program_hash) | `qprivately/acom/gates.py` | ✅ registry + execute |
| Objects (claim/evidence/run/task) | `qprivately/acom/objects.py` | ✅ frozen, content-addressed IDs |
| Receipts (transition, merkle roots, V0-V12) | `qprivately/acom/receipts.py` | ✅ sole canonical path |
| Grants (max_value, max_risk_usd, predicates) | `qprivately/acom/grants.py` | ✅ `verify_grant()` — fail closed on unsigned |
| Runs (cost binding) | `qprivately/acom/runs.py` | ✅ cost in every run receipt |
| Reconcile → receipt | `influence/qp/qp_adapter.py` | ✅ 28,928 receipts in dash log |
| Capability router (free-first, paid+approval) | `pogpet/backend/creative/providers/router.py` | ✅ local.* $0 → paid adapters |
| fal adapter + ledger pattern | `pogpet/backend/creative/providers/fal.py` | ✅ request_id + `fal_credits.jsonl` |
| Human tasks | `influence/dash` human_actions table | ✅ 5 open (social claims) |
| Notifications | `influence/dash/notifications.py` | ✅ SMS + email + feed |
| Predictions before decide | `influence/dash/hloop.py` HLoop | ✅ present → decide |
| Campaign blueprints | `agentcom/campaigns/BLUEPRINT.md` | ✅ evidence bindings + M/H tasks |
| Campaign lifecycle | `workerkit/campaign.py` | ✅ status + cost_usd + runs |
| Dash receipts in UI | `influence/dash/store.py` live_state | ✅ receipt_id, evidence_root, gates |

---

## The runtime loop

```
┌──────────────────────────────────────────────────────────────┐
│                        RUNTIME LOOP                          │
│                                                              │
│  1. INTENT      agent/owner wants action (post, generate,    │
│                 list, spend)                                 │
│                                                              │
│  2. GRANT CHECK qprivately verify_grant()                    │
│                 capability? constraints? predicates? expiry?  │
│                 unsigned → FAIL CLOSED, no exceptions        │
│                                                              │
│  3a. FREE      route local.* adapter → execute → verify     │
│                                                              │
│  3b. PAID      human task created (spend confirm)            │
│                → notification (SMS if high)                  │
│                → human approves → grant minted (single-use)  │
│                → execute with grant → verify                 │
│                                                              │
│  4. VERIFY     G1-G5 gates (see VERIFICATION-GATES.md)      │
│                + image QC gates for generated assets         │
│                                                              │
│  5. RECEIPT    QP transition receipt with:                  │
│                claim + evidence + gates + grant + run        │
│                run includes: model, tool_calls, cost         │
│                                                              │
│  6. LEDGER     append cost line to provider ledger          │
│                (fal_credits.jsonl, meshy_credits.jsonl…)    │
│                                                              │
│  7. AUDIT LIST dash shows: action · channel · cost ·         │
│                gates · receipt_id · timestamp                │
└──────────────────────────────────────────────────────────────┘
```

---

## The audited action list (what you asked for)

Dash gets a new **Actions** view. Every row:

```
time        channel    action              cost      gates    receipt
─────────────────────────────────────────────────────────────────────
12:04:11    fal        flux/dev image      $0.025    6/6 ✓   receipt:a1b2…
12:03:47    etsy       PATCH listing       $0.00     6/6 ✓   receipt:c3d4…
12:01:22    qwen       qwen-plus chat      $0.001    6/6 ✓   receipt:e5f6…
11:58:03    fal        recraft style       $0.005    6/6 ✓   receipt:g7h8…
11:55:19    x          POST tweet          $0.015    6/6 ✓   receipt:i9j0…
11:52:44    prodigi    quote card          $0.00     6/6 ✓   receipt:k1l2…
```

Columns: timestamp · channel · action · cost · gates (n/n) · receipt_id ·
status (PASS/FAIL/UNKNOWN). Click → full receipt with evidence.

**Filters:** by channel · by campaign · failures only · spend only
**Totals row:** today's spend, this campaign's spend, per-channel breakdown

### Data model

```sql
-- audited actions (one row per API call)
CREATE TABLE actions (
  id INTEGER PRIMARY KEY,
  at TEXT NOT NULL,              -- ISO timestamp
  channel TEXT NOT NULL,         -- fal | qwen | etsy | x | prodigi | ...
  action TEXT NOT NULL,          -- flux/dev image | PATCH listing | POST tweet
  sku TEXT,                      -- KEYCHAIN-PET (nullable)
  campaign_id INTEGER,           -- nullable
  cost_usd REAL DEFAULT 0,       -- 0.025
  cost_cents INTEGER DEFAULT 0,  -- 3 (integer math)
  currency TEXT DEFAULT 'USD',
  external_id TEXT,              -- listing_id, tweet_id, request_id
  gates_passed INTEGER,          -- 6
  gates_total INTEGER,           -- 6
  receipt_id TEXT,               -- receipt:a1b2c3d4
  status TEXT,                   -- PASS | FAIL | UNKNOWN
  grant_id TEXT,                 -- single-use grant (paid actions)
  payload_hash TEXT,             -- sha256 of request (no secrets)
  response_hash TEXT,            -- sha256 of response
  created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX idx_actions_at ON actions(at);
CREATE INDEX idx_actions_channel ON actions(channel);
CREATE INDEX idx_actions_campaign ON actions(campaign_id);
CREATE INDEX idx_actions_status ON actions(status);
```

### Provider ledgers (append-only JSONL)

Keep the pogpet pattern — one ledger per provider, same directory:

```
dash/ledger/fal.jsonl        {"at": "...", "endpoint": "fal-ai/flux/dev", "cost_usd": 0.025, "request_id": "...", "owner": "...", "action_id": 123}
dash/ledger/qwen.jsonl       {"at": "...", "model": "qwen-plus", "tokens_in": 500, "tokens_out": 200, "cost_usd": 0.001, "action_id": 124}
dash/ledger/etsy.jsonl       {"at": "...", "action": "PATCH listing", "listing_id": "...", "cost_usd": 0, "action_id": 125}
dash/ledger/x.jsonl          {"at": "...", "action": "POST tweet", "tweet_id": "...", "cost_usd": 0.015, "action_id": 126}
```

Ledger line ⟷ action row via `action_id`. Receipts bind both.

---

## Spend gates (the money flow)

### Grant lifecycle

```
1. Pipeline needs paid action (fal image, ad spend, etc.)
2. Check: is there an active grant covering capability + amount?
   → verify_grant(grant, action, facts, now)
3. No grant → create human task:
     "Approve: fal flux/dev image ($0.025) for KEYCHAIN-PET"
     urgency: high if >$1, medium otherwise
4. Notification: dash bell (+ SMS if amount > threshold)
5. Human approves → single-use grant minted:
     {
       "subject": "owner",
       "capability": "fal.flux_image",
       "constraints": {"max_value": 0.025, "max_calls": 1},
       "predicates": ["action.channel == fal", "action.cost_usd <= 0.025"],
       "expiry": "<now + 1h>",
       "signature": "…"  // owner signs
     }
6. Execute with grant → verify → receipt (grant_id in receipt)
7. Grant marked used (single-use — can't replay)
```

### Budget caps

```python
# pipeline/gates/spend.py
CAMPAIGN_BUDGETS = {
    "xmas-2026": {"cap_usd": 50.00, "spent_usd": 12.40},
}

def check_budget(campaign_id, cost_usd) -> bool:
    """Fail closed: no budget → no spend. No silent overruns."""
    budget = CAMPAIGN_BUDGETS.get(campaign_id)
    if not budget:
        return False  # no budget configured = no spend
    return (budget["spent_usd"] + cost_usd) <= budget["cap_usd"]
```

### Cost table (so every action knows its price)

```python
# pipeline/costs.py
COSTS_USD = {
    "fal.flux_schnell": 0.01,
    "fal.flux_dev": 0.025,
    "fal.recraft": 0.04,
    "fal.recraft_style": 0.005,
    "fal.flux_lora_train": 2.00,
    "fal.birefnet": 0.01,
    "fal.kling_video": 0.25,
    "qwen.qwen_turbo": 0.0001,      # per call est
    "qwen.qwen_plus": 0.001,
    "qwen.image_3_std": 0.033,      # $0.003 + $0.03
    "qwen.image_3_pro": 0.043,
    "qwen.wan_27": 0.03,
    "qwen.wan_27_pro": 0.075,
    "higgsfield.soul_id": 2.50,
    "higgsfield.soul_2": 0.005,
    "x.post_plain": 0.015,
    "x.post_url": 0.20,
    "etsy.listing_update": 0.0,
    "prodigi.quote": 0.0,
    "shopify.product_push": 0.0,
}
```

Free actions still get action rows (cost $0.00) — the audit list is complete.

---

## How it plugs into what exists

### 1. pogpet provider router → dash runtime

The router already resolves capability → adapter with free-first + approval.
Dash runtime wraps it:

```python
# pipeline/adapters/base.py
def run_with_receipt(capability, payload, campaign_id=None):
    # 1. resolve (free first)
    adapter = router.resolve(capability, allow_paid=payload.get("allow_paid"))
    # 2. grant check if paid
    if adapter.paid:
        grant = require_grant(capability, estimated_cost(payload))
        # → human task if no grant
    # 3. execute
    result = adapter.run(payload)
    # 4. verify (G1-G5)
    verified = verify_result(channel, result, payload)
    # 5. receipt
    receipt = verified.receipt()
    # 6. ledger + action row
    log_action(channel, action, cost, receipt)
    return verified
```

### 2. qprivately grants → spend gate

`verify_grant()` is already written. Dash uses it directly:

```python
from acom import grants
ok = grants.verify_grant(grant, action, facts, now_iso)
if not ok["ok"]:
    create_human_task("spend_approval", action)  # fail closed → human
```

### 3. QP receipts → dash actions

`qp_adapter.project_receipt()` pattern extends to action receipts.
`receipts.jsonl` gets action entries alongside reconcile entries.

### 4. human_actions → spend confirm UI

Existing table + task-start + walk_prompt already work.
Add: `amount_usd` column (or store in instructions JSON),
`approve`/`reject` endpoints already exist as patterns.

### 5. agentcom campaigns → dash campaigns

BLUEPRINT.md's M-tasks/H-tasks map to dash human_actions.
Evidence bindings map to QP evidence. 12-gate states map to our gates.

### 6. workerkit campaign.py → campaign lifecycle

Status transitions (created → researching → building → grading → submitted)
+ cost_usd tracking. Dash campaign table mirrors this.

---

## API surface (dash)

```
# audited actions
GET  /api/actions?channel=fal&campaign=xmas-2026&status=FAIL&limit=50
GET  /api/actions/totals?campaign=xmas-2026
     → {total_usd, by_channel: {fal: 1.20, x: 0.03}, count}

# spend gates
POST /api/grant/request     {capability, amount_usd, campaign_id}
     → creates human task, returns task_id
POST /api/grant/approve     {task_id}
     → mints single-use grant
GET  /api/budget/{campaign} → {cap_usd, spent_usd, remaining}

# receipts
GET  /api/receipt/{id}      → full QP receipt + evidence
GET  /api/action/{id}       → action row + receipt + ledger line
```

---

## MCP tools (pi / agents)

```
runtime.action       # execute capability with full gate pipeline
runtime.quote        # price an action without executing (free, no gate)
runtime.approve      # human approves task (returns grant)
runtime.budget       # check campaign budget
runtime.receipt      # fetch receipt by id
runtime.actions      # list audited actions (read-only)
```

All read tools are free. `runtime.action` on paid capabilities requires
`allow_paid=True` AND a valid grant (or it creates the approval task).

---

## Implementation order

| # | Slice | Touches | Proves |
|---|---|---|---|
| 1 | `actions` table + `/api/actions` | dash store + server | audit list visible |
| 2 | `costs.py` price table | pipeline | every action has a price |
| 3 | Provider ledgers (`dash/ledger/*.jsonl`) | pipeline | per-provider spend trail |
| 4 | `spend.py` budget check + grant request | pipeline/gates | money stops at gate |
| 5 | Wire pogpet router → `run_with_receipt` | pipeline/adapters | free-first + paid+approval |
| 6 | Dash Actions tab (UI) | dash static | owner sees 0.005 fal calls |
| 7 | `/api/grant/*` endpoints | dash server | single-use grants live |
| 8 | Campaign tables + budget | dash db | per-campaign caps |
| 9 | MCP tools | dash mcp.py | pi can quote + act |

---

## The one rule (restated for runtime)

> **No action without a grant check. No grant without a signature.
> No execution without verification. No verification without a receipt.
> No receipt without a cost. No cost without a ledger line.
> The dash shows all of it in one list.**
