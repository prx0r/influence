# Setup Workflow — get any business online in 15 minutes

The setup pipeline is a checklist. Each step has a connector, a gate, and a receipt.
Nothing moves forward until the gate passes.

## The Pipeline

```
1. DOMAIN     → register + DNS + SSL
2. EMAIL      → create mailbox + verify receiving
3. PHONE      → buy number + wire SMS/voice
4. SOCIALS    → claim handles + connect posting
5. WEBSITE    → deploy + verify live
6. RECONCILE  → all checks READY → business is ONLINE
```

## Step 1: DOMAIN

```bash
# Check availability
POST /api/domains/check {"domain": "pow.systems"}

# If available, buy through Porkbun/Cloudflare
# Then point nameservers to Cloudflare:
#   gina.ns.cloudflare.com
#   pete.ns.cloudflare.com
```

**Gate:** DNS resolves, SSL active, NS delegated.
**Receipt:** `domain.registered` + `zone.active`

## Step 2: EMAIL

```bash
# Cloudflare Email Routing → support@pow.systems → tradesprior@gmail.com
# Already done for pow.systems

# Verify by sending test email
```

**Gate:** Inbound email received and parsed.
**Receipt:** `mailbox.receiving`

## Step 3: PHONE

```bash
# Search for number
POST /mcp {"method":"tools/call","params":{"name":"phone.find_gem","arguments":{"country":"GB"}}}

# Buy on dashboard.telnyx.com
# Wire to system
POST /api/backend/{slug}/telnyx/credential {"api_key":"..."}
POST /api/backend/{slug}/telnyx/wire {"connection_id":"...","phone_number":"+44...","base_url":"https://..."}

# Verify SMS
POST /mcp {"method":"tools/call","params":{"name":"phone.send_sms","arguments":{"to":"+44...","text":"test"}}}
```

**Gate:** SMS sent and received, voice call connects.
**Receipt:** `number.provisioned` + `sms.verified` + `voice.verified`

## Step 4: SOCIALS

```bash
# Check handles
POST /mcp {"method":"tools/call","params":{"name":"name.handles","arguments":{"name":"pow.systems"}}}

# Connect via Postiz or manual claim
# Each platform: claim → verify → connect
```

**Gate:** Handle claimed, posting works.
**Receipt:** `social.claimed:{platform}`

## Step 5: WEBSITE

```bash
# Deploy to VPS or Cloudflare Pages
# Verify live
GET /api/backend/{slug}/reconcile → all checks READY
```

**Gate:** HTTP 200, content matches.
**Receipt:** `website.live`

## Step 6: RECONCILE

```bash
POST /api/tradie/{slug}/reconcile
```

Returns all ResourceState rows. Every row must be READY or honest MISSING.

## Status: pow.systems

| Step | Status | Notes |
|------|--------|-------|
| Domain | ✅ Cloudflare zone created | Need to update Porkbun NS |
| Email | ✅ support@pow.systems → Gmail | Routing enabled |
| Phone | ⏳ Number picked (07822 000 272) | Need to buy on Telnyx |
| Socials | ❌ Not started | Need to claim handles |
| Website | ❌ Not started | Need to deploy |
| Reconcile | ❌ Blocked on above | |
