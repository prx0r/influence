# Pipeline repo structure

```
influence/pipeline/
├── __init__.py
├── compilers/           # pack → channel payload
│   ├── __init__.py
│   ├── pack_loader.py   # read + validate oddhobbies listing packs
│   ├── etsy.py          # pack → Etsy PATCH payload
│   ├── shopify.py       # pack → Shopify product payload
│   ├── pin.py           # pack → Pinterest pin payload
│   ├── social.py        # pack → X/IG/TikTok/YT variants
│   └── ad.py            # pack → ad creative payload
├── verifiers/           # G1-G5 gates per channel
│   ├── __init__.py
│   ├── gates.py         # gate primitives + run_gates orchestrator
│   ├── etsy.py          # Etsy listing verifier ✅ tested
│   ├── shopify.py       # Shopify product verifier
│   ├── x.py             # X post verifier
│   └── social.py        # IG/TikTok/YT verifiers
├── gates/               # human confirm + money gates
│   ├── __init__.py
│   └── human_confirm.py # task creation + approval polling ✅
├── adapters/            # push to channel (wraps stevejobless publishers)
│   ├── __init__.py
│   ├── etsy.py          # Etsy PATCH executor
│   ├── shopify.py       # Shopify product create/update
│   ├── x.py             # wraps stevejobless twitter adapter
│   └── social.py        # wraps IG/TikTok/YT adapters
└── campaign.py          # orchestrate: compile → confirm → push → verify → receipt
```

## Data flow

```
oddhobbies/stores/*/listings/*.json
        │
        ▼
   pack_loader.load(sku)
        │
        ▼
   compilers.etsy.compile(pack)  →  payload
        │
        ▼
   gates.human_confirm.create_task("push_listing", payload)
        │  (wait for approval)
        ▼
   adapters.etsy.push(payload)  →  response (listing_id)
        │
        ▼
   verifiers.etsy.verify_listing(listing_id, expected)  →  Verified
        │
        ▼
   receipt = verified.receipt()  →  receipts.jsonl
        │
        ▼
   dash notification + task DONE
```

## Key invariants

1. **Nothing publishes without human_confirm** (AGENTS.md rule 2)
2. **Nothing is "done" without a receipt** (VERIFICATION-GATES.md)
3. **Receipt requires all gates PASS** (qprivately spec)
4. **Secrets never in pipeline code** — vault only
5. **Pack is source of truth** — compilers never invent values
6. **Recipes never call providers** — capability router resolves (VISUAL-PROVIDERS.md)
7. **Every generated asset gets QC gates** — identity, hallucination, text, brand (VISUAL-PROVIDERS.md)
8. **Build less, verify more** — platforms are workers, we own recipes + taste + receipts
