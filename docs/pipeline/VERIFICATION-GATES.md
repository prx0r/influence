# Verification Gates — proving something actually happened

> Foundation doc. Every channel action (post, listing, ad) goes through
> this gate pipeline before it counts as done. Built on QP (qprivately)
> formal spec: claim + evidence + gates → content-addressed receipt.

---

## The problem

"Posted" is not a boolean an agent can claim. It's a **verified fact**
that requires:

1. **The action was attempted** (API call made)
2. **The API confirmed success** (response with external ID)
3. **Independent verification** (fetch it back, prove it exists)
4. **Receipt recorded** (content-addressed, chained, replayable)

A tweet that returns 200 but is later deleted = not posted.
A listing that says "active" but has 0 images = not sellable.

---

## Gate taxonomy

### G1 — Attempt gate (was the call made?)
```
predicate: API call returned HTTP 2xx
evidence:  request_id, endpoint, timestamp, response_code
```
This is the weakest gate. Passing G1 alone means nothing.

### G2 — Response gate (did the API accept?)
```
predicate: response contains external_id AND status=success
evidence:  external_id (listing_id, tweet_id, pin_id, product_id),
           status field, full response body hash
```
Etsy: `listing_id` in PATCH response, state=active
X: `data.id` in POST /2/tweets response
Shopify: `product.id` in products.json response

### G3 — Verification gate (does it actually exist?)
```
predicate: independent GET returns the object with expected fields
evidence:  fresh GET response, field-by-field diff vs expected
```
The **100% gate**. Not "the API said ok" — "I fetched it back and it's there."

Per-channel verification:
| Channel | Verify method | What to check |
|---|---|---|
| Etsy | GET /listings/{id} | title, tags, price, state=active, images>0 |
| Shopify | GET /products/{id} | title, status=active, variants, publication_count |
| X | GET /2/tweets/{id} | text matches, created_at within window |
| Instagram | GET /{ig-media-id} | status_code=FINISHED, permalink exists |
| TikTok | GET /v2/post/publish/status/fetch/ | PUBLISH_COMPLETE |
| YouTube | GET /videos?id={id} | status.uploadStatus=uploaded, privacyStatus |
| Pinterest | GET /pins/{id} | title, description, board, image |

### G4 — Content gate (is it the RIGHT thing?)
```
predicate: verified object matches the intended payload
evidence:  field-by-field comparison: title, tags, description, price
```
A post that went live with the wrong price = FAIL even if G1-G3 pass.

### G5 — Freshness gate (is it still true?)
```
predicate: verification re-run within acceptable window
evidence:  verification timestamp, re-verification result
```
Listings get taken down. Tweets get deleted. Freshness re-checks catch drift.

---

## QP integration

Every verified action produces a QP receipt:

```json
{
  "claim": {
    "statement": "Etsy listing KEYCHAIN-PET is live with correct price",
    "domain": "distribution.etsy",
    "result": "TRUE"
  },
  "evidence": [
    {"metric": "api.response_code", "value": "200", "source": "etsy_api"},
    {"metric": "listing.state", "value": "active", "source": "etsy_api"},
    {"metric": "listing.title", "value": "Personalized Pet Keychain...", "source": "etsy_api"},
    {"metric": "listing.price", "value": "9.99", "source": "etsy_api"},
    {"metric": "listing.tags_count", "value": "12", "source": "etsy_api"},
    {"metric": "verify.fetched_at", "value": "2026-10-10T12:00:00Z", "source": "verify"}
  ],
  "gates": [
    {"id": "g1-attempt-v1", "result": "PASS"},
    {"id": "g2-response-v1", "result": "PASS"},
    {"id": "g3-verify-v1", "result": "PASS"},
    {"id": "g4-content-v1", "result": "PASS"},
    {"id": "evidence-fresh-v1", "result": "PASS"},
    {"id": "no-duplicate-v1", "result": "PASS"}
  ]
}
```

If ANY gate fails → claim stays UNKNOWN or FALSE → action is not "done."

---

## Implementation: pipeline/verifiers/

```python
# pipeline/verifiers/base.py
class Verifier:
    channel: str
    def attempt(self, payload) -> GateResult      # G1
    def response_ok(self, response) -> GateResult  # G2
    def verify_exists(self, external_id) -> GateResult  # G3
    def verify_content(self, external_id, expected) -> GateResult  # G4
    def receipt(self, claim, evidence, gates) -> dict  # QP receipt
```

Each channel implements this. The orchestrator never marks "done"
until all gates PASS and receipt is written to `receipts.jsonl`.

---

## Human task flow (dash)

When a gate fails or needs approval:

```
1. Pipeline hits human_confirm gate
2. Task created in dash (human_actions table)
3. Notification: SMS to brand phone + dash bell
4. Human opens task → sees: what, why, preview, approve/reject
5. Human approves → pipeline continues
6. Human rejects → pipeline stops, receipt records rejection
```

Task urgency blend (from notifications.py):
```
urgency = f(title, instructions, risk)
```
Publishing = medium risk. Money spend = high risk. Both need human.

---

## Notification flow

```
Action → gate evaluation → result
  │
  ├─ all PASS → receipt logged → silent (just dash feed)
  ├─ G1/G2 FAIL → immediate notification (something broke)
  ├─ G3 FAIL → immediate notification (API lied or object vanished)
  ├─ G4 FAIL → notification + human task (wrong content live)
  └─ human_confirm needed → human task + SMS (if urgent)
```

Channels: dash bell (always) · SMS (urgent only) · email (digest).

---

## The one rule

> **An action is not done until a receipt says it's done.**
> The receipt requires all gates PASS. Gates require evidence.
> Evidence requires an independent fetch, not just an API response.

This is the foundation everything else (campaigns, social, ads) builds on.
