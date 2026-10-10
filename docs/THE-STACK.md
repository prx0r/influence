# THE STACK — influence is the main repo

> **Stop mixing these up.** This is the map. When lost, come here.

---

## One sentence

**influence** is the ops plane + human dashboard. **bgraph** is the brand identity graph it reads. **oddhobbies** is product truth. **pogpet** is the consumer site. **qprivately** is law. **agentcom.org** is the public ops domain.

---

## Repo roles (do not swap)

```
influence     MAIN ops repo
              dash/ = the dashboard you work in
              core/ = identity slots, cmail connectors, phone policy
              qp/   = grants/gates/receipts
              identities/ = per-brand passport JSON
              products/ = product intents (setup.social, influencer-ops, …)

bgraph        BRAND GRAPH (not a UI)
              registry/brands/*.json  → who exists, handles, branches
              influence READS this; never the other way around as truth

oddhobbies    PRODUCT TRUTH
              stores/<store_id>/listings + commerce.db
              what we sell, costs, listings, ads schema

pogpet        CONSUMER SITE
              oddhobb.com / pog.pet mesh→print funnel

qprivately    LAW
              grants, gates, receipts

stevejobless  OPTIONAL brain adapter (vendored)
              NOT the main dashboard
              useful for tradie jobs / domain deals / phone vault
              Do not open this when you mean "the dashboard"
```

---

## Domains

| Domain | What | Owner repo |
|--------|------|------------|
| **agentcom.org** | **Ops home** | influence/dash |
| phone.agentcom.org | Brand phone inbox (SMS + calls) | influence phone edge |
| channels.agentcom.org | channels (existing CF record) | influence later |
| studio.agentcom.org | studio tunnel | influence / freaktown |
| watch.agentcom.org | watch loop tunnel | influence |
| oddhobb.com | OddHobb shop | pogpet |
| grimoirer.com / stonedoorway.com | sibling brands | pogpet later |

---

## The dashboard

| Surface | URL | Use for |
|---------|-----|---------|
| **Influence dash** | `https://agentcom.org` (tunnel → :8793) | **primary UI** — queue, identities, phone, tasks |
| Local dash | `http://127.0.0.1:8793` | dev |
| Phone inbox API | `https://phone.agentcom.org/v1/*` | SMS/calls for agents |
| Steve desk | steve.intelligentothers.xyz (often down) | optional tradie brain only |

Operate dash:

```bash
cd /root/influence
./dash/serve-perm.sh          # ensure dash + tunnel
./dash/serve-perm.sh status
```

---

## Phone (brand family)

| Field | Value |
|-------|--------|
| Number | **+44 7822 000802** (Telnyx, active) |
| Brands | oddhobb · grimoirer · stonedoorway |
| **Public edge** | **https://phone.agentcom.org** |
| Fallback edge | `https://oddhobb-phone.tradesprior.workers.dev` |
| Local proxy | `127.0.0.1:8794` → worker |
| Webhooks | Telnyx → `phone.agentcom.org/v1/telnyx/{sms,call}` |
| Agent auth | vault `ODDHOBB_PHONE_AUTH` |
| Dash tools | `phone.status` · `phone.sms` · `phone.calls` · `phone.callbacks` |
| Outbound | **gated** — dash `phone.send` requires human `confirm:true` |

Influence dash **reads** the phone inbox. It does not own Telnyx billing.

Operate phone edge:

```bash
./dash/serve-perm.sh          # starts dash + phone proxy + tunnels
./dash/serve-perm.sh status
```

---

## Data flow

```
bgraph registry (brands/handles/branches)
        │
        ▼
influence identities/ + dash  ──reads──► oddhobbies packs (products)
        │
        ├── phone.agentcom.org  ◄── Telnyx webhooks (SMS/calls)
        ├── agentcom.org dash   ── human queue / approve
        └── qp/                 ── grants before spend/send

pogpet oddhobb.com  ── storefront (separate from ops dash)
```

---

## Daily “where do I…?”

| Task | Go to |
|------|--------|
| Work the human queue | **agentcom.org** dash |
| See brand phone SMS/calls | dash phone tools or `phone.agentcom.org` |
| Claim socials | oddhobbies `SOCIAL-CLAIM-RUNBOOK.md` + phone number |
| Edit products / listings | **oddhobbies** `stores/oddhobb/listings/` |
| Edit brand handles / branches | **bgraph** `registry/brands/oddhobb.json` |
| Change shop site | **pogpet** |
| Buy domain / legal gates | influence `qp/` + human confirm |
| Steve tradie jobs | stevejobless only if that’s the job |

---

## Phone wiring (done)

1. Number active on Telnyx  
2. Edge deployed: `oddhobb-phone` worker  
3. DNS: `phone.agentcom.org` → worker (proxied)  
4. Telnyx call-control + messaging profile webhooks → `phone.agentcom.org`  
5. Influence dash MCP reads that inbox  
6. Full guide: `/root/oddhobbies/docs/commerce/BRAND-PHONE.md`  

### Remaining human (free portal)

Attach QuickCall messaging profile to the **number** in Telnyx portal so OTP SMS delivers.

---

## Anti-patterns

- Opening stevejobless when you meant the influence dashboard  
- Treating bgraph as product truth  
- Treating oddhobbies as brand identity  
- Auto-send SMS/calls from agents  
- New phone numbers without owner confirm + money gate  
