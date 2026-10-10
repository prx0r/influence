# Visual generation — fal.ai + Qwen/DashScope

> For the distribution pipeline: product images, social creatives, ad variants.
> Both are API-first. human_confirm on anything that publishes.

---

## fal.ai

**What:** Hosted inference for FLUX, SDXL, Kling, Veo, and more.
**Auth:** `FAL_KEY` env / vault. Pay per generation.
**MCP:** fal has an MCP server (`@fal-ai/mcp`) — tools for image/video gen.

### Key models for us
| Model | Use | Cost (est) |
|---|---|---|
| `fal-ai/flux/dev` | Product hero images, social creatives | ~$0.025/image |
| `fal-ai/flux/schnell` | Fast drafts, previews | ~$0.01/image |
| `fal-ai/recraft-v3` | Brand-consistent illustrations | ~$0.04/image |
| `fal-ai/kling-video/v1/standard/text-to-video` | TikTok/Reels B-roll | ~$0.25/5s |

### API pattern
```python
import fal_client
result = fal_client.subscribe("fal-ai/flux/dev", arguments={
    "prompt": "brick-style pet keychain on warm cream background, product photo",
    "image_size": "landscape_16_9",
    "num_images": 1,
})
url = result["images"][0]["url"]
```

### MCP integration
```
fal-ai MCP server exposes:
  text_to_image, image_to_image, image_upscale, text_to_video
```
Wire into dash agent chat as read-only tools. human_confirm on publish.

---

## Qwen / DashScope (Alibaba)

**What:** Alibaba's model platform. Qwen for text/vision, Wan for image gen.
**Auth:** `DASHSCOPE_API_KEY` ✅ in vault.
**Base:** `https://dashscope-intl.aliyuncs.com/api/v1` ← **international endpoint** (China endpoint rejects this key)
**Status:** Key lists 176 models ✅ but generation returns `AccessDenied.Unpurchased` — need to activate models in Alibaba Cloud console.

### Available models (verified listing)
| Model | Capabilities | Price (per 1M tok) |
|---|---|---|
| `qwen3.8-max` | TG + VU + Reasoning, 1M context | $2 in / $6 out |
| `qwen3.8-flash` | TG + VU + Reasoning, 1M context | $0.15 in / $0.47 out |
| `qwen3.8-omni-flash` | Multimodal (text+image+audio+video) | $0.15 in / $0.47 out |
| `decision-model-preview` | Classification, scoring, routing | free |

**TG** = text generation · **VU** = visual understanding

### To activate
1. Log into Alibaba Cloud console → Model Studio
2. Activate qwen3.8-flash (cheapest) and qwen3.8-omni-flash (multimodal)
3. Key already works on intl endpoint — no key change needed

### API pattern
```python
import urllib.request, json
def qwen_chat(prompt, model="qwen-plus"):
    body = json.dumps({
        "model": model,
        "input": {"messages": [{"role": "user", "content": prompt}]},
    }).encode()
    req = urllib.request.Request(
        "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
        data=body,
        headers={"Authorization": f"Bearer {DASHSCOPE_KEY}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())
```

---

## Pipeline integration

```
Product pack
    │
    ├─→ qwen-plus: generate listing copy variants (A/B)
    ├─→ qwen-vl-max: QC existing product photos
    ├─→ fal flux: generate social creatives from pack assets
    ├─→ fal kling: generate short video B-roll
    │
    └─→ human_confirm gate → publish
```

### Where each fits
| Task | Model | Why |
|---|---|---|
| Listing title/desc A/B | qwen-plus | cheap, fast, good English |
| Tag optimisation | qwen-turbo | classification, free-ish |
| Product photo QC | qwen-vl-max | vision, checks quality |
| Social hero image | fal flux/dev | best quality for product shots |
| Social draft/preview | fal flux/schnell | cheap iteration |
| TikTok B-roll | fal kling | video from prompt |
| Ad creative variants | fal flux/recraft | brand-consistent |

---

## Cost control

- **human_confirm before any paid generation** that will publish
- **schnell for drafts**, dev for final
- **batch generation** — one pack → all channel creatives in one call where possible
- **budget cap per campaign** — hard stop at cap, no exceptions
- Vault keys: `FAL_KEY` (need to add), `DASHSCOPE_API_KEY` ✅

---

## Status

| Item | State |
|---|---|
| DASHSCOPE_API_KEY | ✅ vault |
| FAL_KEY | ❌ not in vault yet |
| fal MCP server | available, not wired |
| Qwen API | verified reachable |
| Pipeline integration | stubs ready, models not wired |
