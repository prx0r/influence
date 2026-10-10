# Entity Goals — A-goal registries per brand/supplier

> Every entity in the dash (brand or supplier) has a goal registry.
> Goals keep agents on task and humans tracking. Built on qprivately ATASK:
> `A-goal → A-tasks → A-logs → A-proof → DONE`.
>
> **Core law: goal DONE is DERIVED, never stored.** It cannot drift from tasks.

---

## Model

```
ENTITY (brand: oddhobb | supplier: jlc)
  └── GOAL (one active end-state, checkable acceptance)
        ├── acceptance indices (numbered, each needs a DONE task)
        └── TASKS (each maps to indices, carries acceptance + evidence)
              ├── status: PROPOSED → JUSTIFIED → EXECUTING → REPORTED → DONE
              │           PAUSED (cites h-task) · REJECTED (re-enters PROPOSED)
              ├── A-LOGS (every action appends: task, action, indices, evidence)
              └── A-PROOF (validator re-runs everything → GREEN → DONE)
```

### Goal
```json
{
  "id": "goal-oddhobb-q4-001",
  "entity": "brand:oddhobb",
  "title": "Q4: 5-8 excellent listings live",
  "acceptance": [
    "5+ listings have real product imagery",
    "all listings have dims + materials + personalisation",
    "delivery estimates honest (match Prodigi windows)",
    "pricing includes real manufacturing costs"
  ],
  "status": "derived", 
  "priority": "P0",
  "deadline": "2026-10-24"
}
```

### Task
```json
{
  "id": "task-001",
  "goal_id": "goal-oddhobb-q4-001",
  "covers": [0, 1],
  "title": "Halloween + Xmas cards: full listing pass",
  "acceptance": "both listings have title/tags/desc/materials/personalisation",
  "evidence_required": ["etsy GET showing fields", "receipt"],
  "status": "DONE",
  "receipt_id": "receipt:..."
}
```

No acceptance without evidence. Refused at creation.

---

## Human boundaries (A-ask)

Agents escalate to human ONLY at genuine boundaries:

| Boundary | Example | Dash surface |
|---|---|---|
| AUTHORIZATION | Approve Etsy push, approve spend | human task + approve button |
| SECRET | Paste API key, OAuth click | vault box + instructions |
| PREFERENCE | Pick design A vs B | options in task |
| PHYSICAL | Print sample, check Croc fit | human task with photo |
| IDENTITY | Claim social handle (CAPTCHA) | claim kit + instructions |
| AMBIGUITY | Two valid interpretations | question in task |

**Proof-of-attempt gate:** agent must show ≥2 attempts + failed checkable
evidence before escalating (except PHYSICAL/IDENTITY). No lazy escalation.

Status-flapping without evidence = farming, flagged.

---

## Human keypad (from ATASK)

```
0 accept recommendation    5 approve
1 ready orders             6 deny + replan
2 status                   7 answer / file correction
3 blockers                 8 expand
4 pick option 1-7          9 halt / resume
```

Every press recorded with timestamp + context. The join is training data.

---

## Event stream (canonical)

All goal/task events append to the existing action ledger + receipts:

| Event | Source |
|---|---|
| task.status | goal system |
| run.started/finished | pipeline execution |
| validator.passed/failed | gates |
| resource.used | costs (every $0.005 fal call) |
| human.asked / human.choice | human_confirm gate |
| goal.done | DERIVED when all indices covered |
| session.outcome | digest on close |

---

## Autonomy metrics (per entity)

```
AutonomyRate = done / (done + h-promotions)
```

Tracked: h-rate per done · $ requested vs granted · post-escalation success.
Verdict per entity: "healthy" vs "collecting."

---

## Decomposition pattern

```
GOAL (entity-level, e.g. "Q4: catalogue excellent")
  ├── TASK (channel-level, e.g. "Etsy listings pass")
  │     ├── ACTION (compile listing payload)
  │     ├── HUMAN (approve push)
  │     ├── ACTION (PATCH via API)
  │     └── VERIFY (G1-G4 gates → receipt)
  ├── TASK (e.g. "Pinterest pins for top 5")
  └── TASK (e.g. "buying journey verified end-to-end")
```

Tasks map to acceptance indices. Actions feed receipts. Receipts prove tasks.
Tasks prove goals. Nothing stored, everything derived.

---

## Q4 OddHobb registry (seed)

See `pipeline/goals.py --seed-q4`. Goals:

1. **Q4-001** [P0] Catalogue excellent (5-8 listings) — deadline Oct 24
2. **Q4-002** [P0] Buying journey works end-to-end — deadline Oct 24
3. **Q4-003** [P0] Distribution experiment live (Pinterest + 1 paid) — deadline Oct 31
4. **Q4-004** [P1] Demand review loop running (weekly) — recurring
5. **Q4-005** [P0] Supplier outreach (JLC + warehouse pilot) — deadline Oct 31
