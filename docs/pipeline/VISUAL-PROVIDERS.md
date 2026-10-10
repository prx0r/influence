# Visual providers — capability router + image QC gates

> Companion to `VISUAL-GENERATION.md`. Captures the architecture decision:
> **OddHobb owns transformation recipes + product recipes + taste + commerce.
> Platforms are workers, not infrastructure.**
>
> Source research: 2026-10-10 agent deep-dive across Alibaba, fal, Higgsfield, ComfyUI.
> Decision: **build less. Verify more.**

---

## The rule

```
OddHobb  = transformation recipes + product recipes + taste + commerce
fal      = model supermarket + LoRA lab + emergency ComfyUI runtime
Alibaba  = cheap/high-volume core generation + text/multi-image editing
Higgsfield = prebuilt identity/product-marketing workflows
```

We never build: training infrastructure, GPU hosting, workflow orchestration,
preset catalogs, LoRA trainers. We build: **recipes, routers, QC gates, receipts.**

---

## Capability router (not provider router)

Products never call a provider. They call a capability:

```python
transform(
    capability="identity_transform",
    references=[...],
    instruction="...",
    contract={...},
)
```

The router resolves capability → provider:

| Capability | Default provider | Fallback |
|---|---|---|
| `subject_cutout` | fal BiRefNet | rembg local |
| `identity_transform` (human, has Soul ID) | Higgsfield Soul 2 | Qwen Image 3 |
| `identity_transform` (pet/no Soul ID) | Alibaba Qwen Image 3 | fal flux-2-pro-edit |
| `text_heavy_art` | Alibaba Qwen Image 3 | fal qwen-image-3 |
| `consistent_image_set` | Alibaba Wan 2.7 | fal wan |
| `brand_illustration` | fal Recraft style_id | — |
| `product_packshot` | Higgsfield Product Shots | fal flux |
| `marketplace_image` | Higgsfield Marketplace Design | — |
| `local_edit` | Alibaba Qwen Image 3 edit | fal flux-kontext |
| `bespoke_chain` | fal-hosted ComfyUI | — |

Providers change constantly. Recipes never do.

---

## Transformation library (ingredients, not products)

| Transform | Input | Implementation | Products it feeds |
|---|---|---|---|
| `subject_cutout_v1` | photo | fal BiRefNet | wrap, stickers, tags, cards |
| `pet_santa_v1` | pet refs | Qwen Image 3 edit | wrap, cards, poster, tags |
| `editorial_gouache_v1` | person refs | Qwen / Recraft style | cards, prints |
| `sports_champion_v1` | person refs | Soul 2 / FLUX multi-ref | cards, posters |
| `news_portrait_v1` | person ref | Qwen / FLUX | cards |
| `christmas_badge_v1` | person/pet | Qwen + cutout | wrap, labels, stickers |
| `oddhobb_woodcut_v1` | subject | Recraft style ID | cards, wrap, print |
| `product_packshot_v1` | product render | Higgsfield Product Shots | Etsy/Shopify |
| `marketplace_listing_v1` | product render | Higgsfield Marketplace | Etsy/Shopify |
| `natural_edit_v1` | generated asset | Qwen / FLUX edit | "brown paper", "less snow" |
| `scene_set_v1` | 1–9 refs | Wan 2.7 image set | card series, comics |
| `oddhobb_style_lora_v1` | curated outputs | fal FLUX LoRA | entire catalog |

**None of these is a product.** They are reusable ingredients:

```
pet_santa_v1
    ↓
┌──────────┬──────────┬──────────┐
wrap       card        poster
recipe     recipe      recipe
└──────────┴──────────┴──────────┘
```

One expensive transformation → many products. This is the credit economics.

---

## Progression (don't over-train)

```
Prompt only
    ↓
Prompt + reference
    ↓
Reusable Recraft style_id ($0.005)
    ↓
LoRA only when a style deserves permanent specialization ($2)
```

Identity:
```
reference images
    ↓
Higgsfield Soul ID ($2.50, only for high-frequency humans)
```

---

## Image QC gates (extends VERIFICATION-GATES.md)

Every generated image goes through gates **before** it becomes an ingredient:

| Gate | Predicate | Evidence |
|---|---|---|
| `qc-identity-v1` | Subject matches reference (eyes, markings, proportions) | Qwen-VL comparison score |
| `qc-no-hallucination-v1` | No extra limbs/animals/people | detector count matches expected |
| `qc-text-v1` | Text (if any) is legible and spelled correctly | OCR check |
| `qc-composition-v1` | Subject fully in frame, correct aspect | bounding box analysis |
| `qc-brand-v1` | Matches OddHobb taste bar (no neon, no metal, warm) | style classifier or human |
| `qc-fresh-v1` | Generated within session window | timestamp |

A failed image never reaches a product recipe. It goes back to the queue
with the failure reason, or to a human task if it keeps failing.

```python
# pipeline/verifiers/image.py (stub)
def verify_image(image_url, reference_urls, checks) -> Verified:
    """G1-G4 for a generated image."""
    # G1: image exists at URL, downloads OK
    # G2: dimensions/format match contract
    # G3: re-fetch and hash — still there
    # G4: QC checks (identity, hallucination, text) all pass
```

---

## Recipe format (steal Higgsfield's preset architecture)

Higgsfield Marketing Studio exposes a **preset catalog** — recipes refer to
`preset_id`, not giant prompts. We do the same:

```json
{
  "id": "pet_santa_v1",
  "capability": "identity_transform",
  "references": {"subject": "pet", "min_images": 1, "preferred_images": 3},
  "instruction": {
    "template": "Transform the same pet into a tasteful Christmas portrait wearing a small classic Santa hat. Plain background."
  },
  "preserve": ["eye colour", "fur markings", "face proportions", "ear shape"],
  "output": {"aspect_ratio": "1:1", "background": "transparent-preferred"},
  "qc": {"identity": true, "no_extra_animals": true}
}
```

Recipes refer to `transform_id`. The router resolves. Gates verify.

---

## The pet-Santa wrapping paper demo (first end-to-end)

```
1. Upload 3–5 pet images, confirm identity
2. Rank best references
3. Qwen Image 3 (direct Alibaba): preserve eyes/fur/muzzle/ears + Santa hat + plain bg
4. BiRefNet: clean transparent motif        ← QC gates here
5. Deterministic repeat recipes: classic / scattered / badge
6. Show wrapping-paper previews
7. "Make it brown paper" → change decoration layer ONLY (no regen)
8. "Green knitted hat" → edit just the pet ingredient
9. Save revision → buy
```

Shows: identity → transform → ingredient → product → natural-language edit → physical object.

---

## Pricing (Singapore, Alibaba direct)

| Model | Cost |
|---|---|
| Qwen Image 3 standard | $0.003 input + $0.03/1K output |
| Qwen Image 3 Pro | $0.003 input + $0.04/1K output |
| Wan 2.7 | $0.03/image |
| Wan 2.7 Pro | $0.075/image |
| fal-hosted Qwen Image 3 | $0.075/image (experiment tax OK, move volume direct) |
| Higgsfield Soul ID | $2.50 one-time |
| Higgsfield Soul 2 | ~$0.0032–0.0057/image |
| fal Recraft style | $0.005 one-time |
| fal FLUX LoRA training | ~$2/run |

**Direct Alibaba for volume. fal for experiments. Higgsfield for identity + packshots.**

---

## What we do NOT build

- ❌ GPU hosting (fal-hosted ComfyUI if needed)
- ❌ Training infra (fal trainers, Alibaba SFT-LoRA)
- ❌ Workflow orchestration (their UIs are fine, our recipes are the orchestration)
- ❌ Preset catalogs from scratch (steal the architecture, own our recipes)
- ❌ Fooocus, IPAdapter_plus, InstantID (maintenance-only, skip)

## What we DO build

- ✅ Transformation recipes (JSON, versioned, QC'd)
- ✅ Product recipes (pack + transform_id → SKU)
- ✅ Capability router (provider-agnostic)
- ✅ Image QC gates (extend VERIFICATION-GATES.md)
- ✅ Receipts for every generated asset
- ✅ Taste bar (human + classifiers)

---

## ComfyUI repos to mine (architecture only, not dependencies)

- Comfy-Org/workflow_templates — subgraph blueprints, workflow JSON
- Comfy-Org/ComfyUI — runtime/API patterns
- Comfy-Org/comfy-cli — agent-friendly execution
- InvokeAI — production UI patterns
- ostris/ai-toolkit, Nerogar/OneTrainer — LoRA training (later)
- ComfyUI-Impact-Pack — detection/detailer examples
