# NORTHSTAR — one name, owned everywhere, touched once

> Check a name across domains + socials + web3 → buy the domain → claim the
> handles → wire email + backend → run the business. Human confirms spend and
> clicks where only humans can. Everything else is machine.

## The loop

```text
namecheck (checker worker)
  domain verify + handles map + ENS
        │ claim_kit
        ▼
steve /api/domains/* (brain)
  prepare → approve → register → wire
        │                    │
   Cloudflare Registrar      │ fallback: Porkbun/Name.com (excluded TLDs)
   API (default, at-cost)    │ then NS → Cloudflare (seconds, any TLD)
        │                    │
        └────── zone live ───┘
                │
   Email Routing → cmail → hello@, support@, agents@
   steve business + kernel + reconcile
   Telnyx number (bought via API) → voice + SMS
   social setup checklist (human claims, machine verifies + connects)
```

## Division of labor (who does what)

| Step | Machine | Human |
|---|---|---|
| Availability (domains, handles, ENS) | ✅ all of it | — |
| Price compare + cheapest-provider pick | ✅ | — |
| Domain purchase | executes | **confirms spend** (one-time token) |
| Billing profile + account agreements | — | **once, in dashboard** |
| Nameservers / zone / routing / mailboxes / business | ✅ all of it | — |
| Social account *creation* | ❌ impossible — see below | **claims handles** (guided checklist) |
| Social API connect (post/read/DM) | ✅ after OAuth | **one OAuth click per platform** |
| Phone number | ✅ Telnyx API buy | confirms spend |
| Quotes, sends, publishes | draft | **confirm** (any autonomy level) |

## Hard honesty section (read before promising more)

1. **No platform allows programmatic social account creation.** Instagram,
   TikTok, X, YouTube all require human signup (anti-bot law of nature).
   What we automate: availability map → claim order → deep links → verify
   claimed handles resolve → connect APIs. Claiming stays a 10-minute human
   task; everything around it is machine.
2. **Cloudflare Registrar API excludes some TLDs** (`.lol`, `.inc`, `.sh`,
   `.cc`, `.new`, …) and premium names. Exotic TLDs buy on Porkbun/Name.com,
   then NS-move to Cloudflare — same end state, one extra hop.
3. **First-time Cloudflare billing + account agreements are dashboard-only.**
   One-time, owner-only, ~5 minutes. After that the API loop is closed.
4. **Meta approvals gate WhatsApp/IG sends**, not our code. Official Cloud
   API path, number owned in the business's own Manager.
5. **500 domains/account** on Cloudflare Registrar. Fine for now; flag at 400.

## Cloudflare-native surface we ride

Registrar API (search/check/register) · Email Routing + Email Service ·
Workers/DO/D1/R2 (cmail) · Workers AI (classify) · Official Cloudflare MCP
servers (bindings, docs, observability) · Queues/Workflows when volume needs
it · Tunnel (steve origin). Registrar + bindings MCP mean agents already
speak this stack — we orchestrate, not reimplement.
