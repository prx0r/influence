# products — index

Every product is one directory entry with the same schema. Kinds: **infra**
(other products depend on it) or **surface** (users touch it). Details in
`product-schemas.md`, graph in `dependency-graph.md`, OS framing in
`OS.md` (factories upstream, plane midstream, doors downstream).

## Infra (products for products)

- `setup.social` — domains, handles, socials, mailbox, number. Everything
  that ends at an identity starts here.
- `funnylab` — the simulate-only comedy loop. Feeds lineages to autopilot,
  judges to eval-api.
- `eval-api` — typed judges as a metered endpoint. Called by lab, ops,
  studio, roast lines.
- `trend-radar` — trends mined into ranked candidates. Feeds spawn.
- `private-studio` — TEE runs plus identity-free setup. Hardens everything.

## Surface (users touch these)

- `instant-influencer` — spawn from scratch.
- `influencer-ops` — manage, post, send, renew.
- `influencer-studio` — content engine on the freaktown bridge.
- `freaktown-autopilot` — the self-running show.
- `watch-loop` — audience side that closes autopilot.
- `clip-farm` — sets cut into scored clips.
- `roast-line` — crowd-work as a service.
- `roast.pet` — upload your pet, get roasted. Etsy storefront + site.
- `party-rooms` — pogtown rooms, gifts, games, hosted.
- `guest-bookings` — outside agents buy stage time.
- `storefront` — influencer stores + merch lines.

## Map (who needs whom)

```
private-studio ─┬─> setup.social ─┬─> instant-influencer ─> influencer-ops
                │                  ├─> roast.pet ──────────> clip-farm
eval-api ───────┤                  └─> party-rooms ────────> guest-bookings
trend-radar ────┘
funnylab ───────> freaktown-autopilot <── influencer-studio
watch-loop ─────> freaktown-autopilot (closes it)
clip-farm ──────> storefront (clips are the ads)
money-proof ────> storefront + ops (gates before doors open)
```
