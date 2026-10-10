# Distribution Pipeline — Product Pack → Every Channel

> Vision captured 2026-10-10. One product pack in `oddhobbies/stores/*/listings/*.json`
> is the atom. Everything downstream is a compiler that turns that atom into
> channel-native payloads, with human_confirm gates on anything that publishes
> or spends money.
>
> Lives in the influence dash (agentcom.org). Repo: `prx0r/influence`.

---

## The thesis

> **Author once, distribute everywhere.**

A product pack already contains everything a channel needs:
title, tags, description, price, taxonomy, shipping profile, cost, supplier.
The pipeline's job is to **compile** that pack into channel payloads,
**preview** them in the dash, **push** behind a gate, and **track** receipts.

No copy-paste. No drift. Every channel stays in sync because they all
read the same source of truth.

---

## Architecture

```
oddhobbies/stores/<store>/listings/<SKU>.json     ← SOURCE OF TRUTH
        │
        ▼
┌─────────────────────────────────────────────────────┐
│              CONTENT COMPILER (influence)           │
│                                                     │
│  pack_loader.py   → parse + validate pack           │
│  etsy_compiler.py → Etsy PATCH payload              │
│  pin_compiler.py  → Pinterest pin title/desc/board  │
│  social_compiler.py → X/IG/TikTok/YT variants      │
│  shopify_compiler.py → Shopify product payload      │
│  ad_compiler.py   → Meta/Pinterest ad creative      │
│                                                     │
│  campaign.py      → group packs → campaign          │
│  scheduler.py     → queue publish times             │
│  receipts.py      → track per-channel status        │
└─────────────────────────────────────────────────────┘
        │
   ┌────┴────┬──────────┬──────────┬──────────┐
   ▼         ▼          ▼          ▼          ▼
 Etsy API  Shopify   Pinterest   X/IG/YT    Meta
 (live)    (token    (via       (adapters  Ads
            needed)   Shopify    in         (later)
                      channel)   stevejobless)
   │         │          │          │          │
   └────┬────┴──────────┴──────────┴──────────┘
        ▼
   DASH (agentcom.org)
   Campaigns tab · receipts · human_confirm · analytics
```

---

## Channel matrix

| Channel | Auth status | Push method | Gate |
|---|---|---|---|
| **Etsy** | ✅ live (listings_w) | REST PATCH | human_confirm |
| **Shopify** | ⚠️ token stale — refresh needed | Admin API products.json | human_confirm |
| **Pinterest** | ✅ via Shopify sales channel (no separate signup) | Shopify publication push | human_confirm |
| **Pinterest Ads** | ❌ needs Pinterest business token | Ads API (later) | approval token (money) |
| **X** | ✅ oddhobb keys in vault | tweepy OAuth1 adapter | human_confirm |
| **Instagram** | ⚠️ password in vault; needs Graph API token | Graph API adapter | human_confirm |
| **TikTok** | ⚠️ password in vault; needs Content Posting app | adapter written | human_confirm + SELF_ONLY until audit |
| **YouTube** | ✅ API key in vault | Data API adapter | human_confirm |
| **Meta Ads** | ❌ needs app + token | Graph Ads API (later) | approval token (money) |

---

## The pack atom

Every listing JSON in `oddhobbies/stores/<store>/listings/` already has:

```json
{
  "sku": "KEYCHAIN-PET",
  "store_id": "oddhobb",
  "state": "active",
  "etsy_listing_id": "4587938693",
  "etsy_title": "Personalized Pet Keychain Figurine",
  "price": 9.99,
  "taxonomy_id": 1552,
  "tags": ["pet keychain", "dog keychain", ...],
  "description": "Turn your dog or cat into...",
  "shipping_profile_id": 316299492609,
  "processing": [3, 8],
  "make": "3d_print",
  "material": "PLA",
  "unit_cost_usd": 1.75,
  "supplier_primary": "MAKR3D",
  "go_live_blocker": null
}
```

The compiler reads this and never asks the same question twice.

---

## Genius workflows

### W1 — Launch a product everywhere (one-click)

```
1. Owner adds/edits pack in oddhobbies/stores/
2. Dash "Launch" button → compiler runs all channels
3. Preview panel shows: Etsy payload · Shopify payload · Pin · X post · IG post
4. Owner approves each (or approve-all)
5. Push executes, receipts logged per channel
6. Campaign created, tracking begins
```

**Definition of done:** one pack → live on Etsy + Shopify + Pinterest + at least one social post, all from one click.

---

### W2 — Seasonal campaign rollout (Xmas, Halloween, Valentine's)

```
1. Owner picks occasion + store
2. Pipeline filters packs by: tags match occasion OR section matches
   (e.g. "Christmas Gifts", "Game Night")
3. Generates campaign brief:
   - Which SKUs to feature
   - Pinterest board name + pin copy per SKU
   - Social post calendar (staggered over N days)
   - Ad creatives (if budget approved)
4. Owner reviews calendar in dash
5. Scheduler queues posts across channels over the campaign window
6. Daily digest: what posted, what's pending, what failed
```

**Genius bit:** the packs already have `sections_forbidden: ["Christmas Gifts"]` for oddhobb — the compiler respects pack-level gates.

---

### W3 — Social campaign from product pack

```
For each pack, generate channel-native variants:

X (Twitter):
  "Your dog as a tiny brick keychain. Upload a photo, approve the
  preview, get it in 5-8 days. £9.99 → [link in bio]"
  (no URL in body — $0.015 vs $0.20)

Instagram:
  Hero image + caption with hook, product, CTA, hashtags
  (from pack tags + brand hashtags)

TikTok:
  Script outline: hook (0-3s) → product reveal (3-8s) → CTA
  (video comes from studio renders or product stills)

YouTube Short:
  Same as TikTok but with end card pointing to shop

Pinterest:
  Pin title = etsy_title (SEO optimised)
  Pin description = first 200 chars of pack description + CTA
  Board = pack's shop_section_target
```

Each variant is a **draft** in the dash. Human confirms. Adapter posts.

---

### W4 — Etsy listing factory (bulk)

```
1. Select N packs (or all in a section)
2. Compiler generates/validates:
   - Title (≤140 chars, keyword-stuffed per Etsy SEO formula)
   - 13 tags (≤20 chars each, no duplicates)
   - Description (structure: hook → what you get → how it works → shipping)
   - Taxonomy (mapped from pack's product type)
   - Materials, processing, shipping profile
3. Preview diff: current Etsy state vs desired state
4. Push PATCH per listing (only changed fields)
5. Receipt: listing_id, fields updated, timestamp
```

**Already proven** — we just did this manually for AI Halloween + Christmas cards. This automates it for all 37 packs.

---

### W5 — Pinterest pin factory

```
Pinterest rides the Shopify sales channel (already linked).
Pipeline:

1. Pack → Shopify product (if not already synced)
2. Pinterest auto-generates pins from Shopify product images
3. But we can also push curated pins:
   - Title: etsy_title (SEO optimised for Pinterest search)
   - Description: pack description + keywords + CTA
   - Board: mapped from shop_section_target
   - Image: best asset from pack's image slots (by suitability flag)

4. Schedule: pin best-sellers first, new arrivals next
5. Track: impressions, saves, outbound clicks (Pinterest Analytics API)
```

**Asset labels already support this** — `oddhobbies/db/ASSET-LABELS.md` has `suitability.pinterest` boolean per asset.

---

### W6 — Ad campaign (Pinterest/Meta) — money gate

```
Same as social but with spend:

1. Campaign brief includes budget cap
2. Ad compiler generates creative variants from pack assets
3. Money gate: single-use approval token (sha256-stored) per campaign
4. Fresh rechecks before spend: price drift ≤10%, budget cap
5. Launch → track ROAS per SKU
6. Kill underperformers automatically (threshold set in campaign)
```

**Rule 3 from AGENTS.md applies:** money moves need approval tokens + fresh rechecks. Fail closed, receipt everything.

---

### W7 — Content refresh (keep listings alive)

```
Weekly sweep:
1. Check Etsy listing views/favourites (API)
2. Flag listings with 0 views in 30 days → suggest tag/desc refresh
3. Flag listings with high views but 0 sales → suggest price or photo test
4. Generate A/B variants for underperformers
5. Owner approves refresh → push
```

---

### W8 — Multi-brand orchestration

```
Same pipeline, multiple stores:

oddhobb    → brick figures, pet gifts, game night
grimoirer  → (brand TBD)
stonedoorway → (brand TBD)
pogtown    → (brand TBD)

Dash shows per-brand:
- Pack count · live listings · campaign status · revenue
- Cross-brand: "this pack's tags overlap with that brand's — merge?"

bgraph is the identity spine; oddhobbies is the commerce truth;
influence is the distribution brain.
```

---

## Database additions (influence)

```sql
-- campaigns
CREATE TABLE campaigns (
  id INTEGER PRIMARY KEY,
  project_id INTEGER,          -- links to projects (brand)
  name TEXT,                   -- "Xmas 2026 Game Night"
  occasion TEXT,               -- halloween | christmas | valentines | generic
  status TEXT,                 -- draft | active | paused | done
  budget_cents INTEGER,        -- NULL = no ads
  starts_at TEXT,
  ends_at TEXT,
  created_at TEXT
);

-- campaign_items (which packs in which channels)
CREATE TABLE campaign_items (
  id INTEGER PRIMARY KEY,
  campaign_id INTEGER,
  sku TEXT,                    -- KEYCHAIN-PET
  store_id TEXT,               -- oddhobb
  channel TEXT,                -- etsy | shopify | pinterest | x | instagram | tiktok | youtube
  status TEXT,                 -- draft | queued | published | failed
  payload_json TEXT,           -- compiled channel payload
  external_id TEXT,            -- listing_id, pin_id, tweet_id, etc.
  published_at TEXT,
  receipt_json TEXT,
  UNIQUE(campaign_id, sku, channel)
);

-- channel_receipts (audit trail)
CREATE TABLE channel_receipts (
  id INTEGER PRIMARY KEY,
  campaign_item_id INTEGER,
  action TEXT,                 -- create | update | publish | delete
  status TEXT,                 -- ok | error | skipped
  response_json TEXT,
  created_at TEXT
);
```

---

## Implementation order

| # | Slice | Why first |
|---|---|---|
| 1 | `pack_loader.py` + schema validation | everything reads packs |
| 2 | `etsy_compiler.py` + `push_etsy.py` | proven live, highest value |
| 3 | Campaign tables + dash Campaigns tab | orchestration surface |
| 4 | `social_compiler.py` (X first — keys in vault) | cheapest channel, adapter ready |
| 5 | Shopify token refresh + `shopify_compiler.py` | unlocks Pinterest via sales channel |
| 6 | `pin_compiler.py` | Pinterest pins from packs |
| 7 | Scheduler (staggered social posts) | campaign automation |
| 8 | Ad compilers (Pinterest/Meta) | money gate, later |

---

## Key files (existing, to wire in)

| File | Role |
|---|---|
| `oddhobbies/stores/*/listings/*.json` | 37 product packs — source of truth |
| `oddhobbies/db/ASSET_LABELS` | per-channel asset suitability |
| `oddhobbies/shop/listings/*.json` | shop-facing listing copies |
| `pogpet/backend/config.py` ETSY_LISTINGS | pet-line listing formula |
| `stevejobless/publisher/adapters/` | X/IG/TikTok/YT push adapters |
| `influence/dash/server.py` | dash backend |
| `influence/core/cmail/social_onboarding.py` | brand social registry |
| `influence/data/social_onboarding.v1.json` | claim state per brand |

---

## Open decisions

1. **Shopify token** — stale. Refresh from admin or re-auth via OAuth?
2. **Pinterest Ads** — worth a business account, or ride Shopify channel only?
3. **Image pipeline** — use existing pogpet renders, or generate per-channel crops?
4. **Scheduler** — systemd timer in influence, or dash-internal loop?
5. **Multi-brand** — start oddhobb-only, or wire grimoirer/stonedoorway from day 1?

---

## The one sentence

> **A product pack is written once; the pipeline compiles it into every
> channel's native format, previews it in the dash, publishes behind a
> human gate, and tracks the receipts — so launching a product everywhere
> takes one click, not twelve tabs.**
