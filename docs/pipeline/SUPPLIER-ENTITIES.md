# Supplier entities — pogpet ↔ dash link for manufacturing relationships

> Suppliers are entities like brands. Each has: identity, contacts, thread
> history, status, and gated outreach. Agents can draft emails (never send
> without human_confirm). Every email in/out is timestamped and retrievable:
> "what's the latest from JLC?" → full thread. "Chase them" → draft follow-up.

---

## Entity model

Suppliers live in the dash DB alongside projects. One table, same receipt pattern.

```sql
CREATE TABLE IF NOT EXISTS suppliers (
  id INTEGER PRIMARY KEY,
  slug TEXT UNIQUE,              -- jlc, makerfabs, nextsmartship, ...
  name TEXT,                     -- JLCPCB / JLC3DP
  role TEXT,                     -- fabrication | integration | fulfilment | print | craft
  status TEXT DEFAULT 'prospect', -- prospect | contacted | quoted | trial | active | paused | dropped
  website TEXT,
  contacts_json TEXT,            -- [{name, email, role, notes}]
  domains_json TEXT,             -- ["jlcpcb.com"] for email matching
  notes TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS supplier_emails (
  id INTEGER PRIMARY KEY,
  supplier_id INTEGER,
  direction TEXT,                -- in | out | draft
  subject TEXT,
  body_text TEXT,
  from_addr TEXT,
  to_addrs TEXT,                 -- JSON list
  sent_at TEXT,                  -- NULL for drafts
  message_id TEXT,               -- cmail/worker ID
  thread_id TEXT,                -- groups replies
  status TEXT DEFAULT 'logged',  -- logged | queued | sent | failed
  receipt_id TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_supp_emails_supplier ON supplier_emails(supplier_id);
CREATE INDEX IF NOT EXISTS idx_supp_emails_thread ON supplier_emails(thread_id);
CREATE INDEX IF NOT EXISTS idx_supp_emails_at ON supplier_emails(sent_at);
```

## Seed suppliers (from oddhobbsuppliers.md)

| Slug | Name | Role | Email | Status |
|---|---|---|---|---|
| jlc | JLCPCB / JLC3DP | fabrication | support@jlcpcb.com | prospect |
| makerfabs | Makerfabs | integration | service@makerfabs.com | prospect |
| nextsmartship | NextSmartShip | fulfilment | sales@nextsmartship.com | prospect |
| china-fulfillment | China Fulfillment Intl | fulfilment | support@china-fulfillment.com | prospect |
| seeed | Seeed Studio Fusion | integration | fusion@seeed.io | prospect |
| elecrow | Elecrow | integration | service@elecrow.com | contacted |
| onebookprint | OneBookPrint | print | (site form) | prospect |
| makr3d | MAKR3D | fabrication (UK 3D) | (existing) | active |
| printie | Printie | fabrication (US 3D) | (existing) | active |
| prodigi | Prodigi | print (paper POD) | (API) | active |

## Email flows

### Inbound (supplier → us)
```
cmail worker receives → notifications.fetch_email picks up
  → match from-domain against suppliers.domains_json
  → insert supplier_emails (direction=in, thread resolved)
  → dash bell + receipt
```

### Outbound (us → supplier, gated)
```
agent drafts → human_confirm gate (ALWAYS for external email)
  → human approves → send via cmail/worker
  → insert supplier_emails (direction=out, status=sent)
  → receipt with message_id
```

**Rule: no agent sends supplier email without human_confirm.**
Drafts are free. Sends need approval. Every send has a receipt.

### Queries (what the owner asked for)
```
"latest from JLC" →
  SELECT * FROM supplier_emails WHERE supplier_id=jlc
  ORDER BY sent_at DESC LIMIT 5

"chase NextSmartShip" →
  last outbound + days since + no reply?
  → draft follow-up (human_confirm before send)

"who haven't we heard from?" →
  suppliers contacted >7d ago with no inbound since
```

## MCP tools (dash)

```
supplier.list              → all suppliers + status
supplier.thread <slug>     → full email thread, newest first
supplier.latest <slug>     → last email either direction
supplier.draft <slug> <subject> <body>  → create draft (free, no gate)
supplier.send <draft_id>   → human_confirm gate → send
supplier.chase <slug>      → draft follow-up based on last thread
supplier.set_status <slug> <status>  → prospect→contacted→quoted→…
supplier.quiet             → contacted, no reply 7d+ (chase list)
```

## Dash UI (Suppliers tab)

```
supplier | role | status | last contact | thread | actions
JLC      | fab  | prospect | —          | 0 msgs | [email] [status]
Elecrow  | integ| contacted| 12d ago    | 3 msgs | [chase] [thread]
```

Each thread view: full history, timestamps, direction badges, draft box.
