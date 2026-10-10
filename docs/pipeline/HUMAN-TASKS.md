# Human Tasks & Notifications — the confirmation layer

> Every autonomous action that publishes, spends, or changes public state
> passes through a human task. The dash is the surface. Notifications
> are the nudge. Receipts are the proof.

---

## Task lifecycle

```
PENDING → STARTED → APPROVED → EXECUTING → VERIFIED → DONE
                 ↘ REJECTED
                 ↘ EXPIRED (timeout)
```

### States

| State | Meaning | Who moves it |
|---|---|---|
| PENDING | Task created, waiting for human | system |
| STARTED | Human opened the task | human (or task-start API) |
| APPROVED | Human said yes | human |
| REJECTED | Human said no | human |
| EXECUTING | Pipeline running the approved action | system |
| VERIFIED | All gates PASS, receipt written | system |
| DONE | Terminal success | system |
| FAILED | Gate failed after approval | system |
| EXPIRED | No human response within timeout | system |

---

## Task creation

Tasks are created by the pipeline when:

1. **human_confirm gate** — action needs approval before executing
2. **gate failure** — something broke, human should know
3. **content mismatch** — wrong thing went live, needs review
4. **key needed** — API token missing/expired, human must provide

```python
# pipeline/gates/human_confirm.py
def create_task(action, payload, urgency="medium"):
    return {
        "title": f"Approve: {action} on {payload['channel']}",
        "instructions": preview_text(payload),
        "risk": risk_score(action),  # publish=0.3, spend=0.8
        "url": payload.get("preview_url"),
        "urgency": urgency,
        "channel": payload["channel"],
        "sku": payload.get("sku"),
        "payload_hash": sha256(json.dumps(payload)),
    }
```

---

## Notification rules

| Event | Dash bell | SMS | Email |
|---|---|---|---|
| Task created (publish) | ✅ | if urgent | daily digest |
| Task created (spend) | ✅ | ✅ | ✅ |
| Task approved | ✅ | — | — |
| Gate failure | ✅ | ✅ | ✅ |
| Verification pass | feed only | — | — |
| Verification fail | ✅ | ✅ | ✅ |

SMS goes to brand phone via `phone.agentcom.org`.
Email goes to brand mailbox via cmail worker.

---

## Dash task API

```
GET  /api/tasks              → list pending + recent
POST /api/task-start         → mark started, get walk_prompt
POST /api/task-approve       → approve, trigger execution
POST /api/task-reject        → reject, log reason
GET  /api/task/{id}/preview  → compiled payload preview
GET  /api/task/{id}/receipt  → QP receipt if done
```

---

## Urgency scoring

From `notifications.py::_urgency_of`:

```
urgency = blend(
    text_match(title+instructions),  # "secret", "key", "token" → higher
    risk_score,                      # from task payload
)
```

- **low** (0.0-0.3): publish approval → batch to morning
- **medium** (0.3-0.6): content mismatch → notify within hour
- **high** (0.6-1.0): money, secrets, live errors → SMS now

---

## Integration with QP

Every human decision produces evidence:

```json
{
  "metric": "human.approval",
  "value": "APPROVED",
  "source": {
    "class": "human",
    "label": "Owner approved Etsy listing push",
    "artifact_hash": "sha256:..."
  },
  "as_of": "2026-10-10T12:00:00Z"
}
```

This evidence feeds the QP receipt. A push without human approval
evidence = receipt FAIL even if the API call succeeded.

---

## The flow (end to end)

```
1. Pipeline compiles payload (e.g. Etsy listing from pack)
2. human_confirm gate fires → task created in dash
3. Notification sent (bell + SMS if urgent)
4. Human opens dash → sees preview → approves
5. Pipeline executes → API call → response
6. Verifier runs G1-G4 → receipt written
7. Task moves to DONE (or FAILED if gates fail)
8. If FAILED → notification + new task for human review
```

Nothing publishes without step 4.
Nothing counts as done without step 6.
