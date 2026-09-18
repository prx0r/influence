# SteveJobless v0.2 — Business Operations Center

## What Changed

v0.1 was a reconciliation bot. v0.2 is a **unified business operations center**.

## New Capabilities

### 1. Credential Vault
Store API keys, tokens, and secrets per business per platform.
- Each business has its own credential set
- Credentials are encrypted at rest
- Never exposed in passports or logs
- agent-vault integration for shared secrets

### 2. Social Posting
Post content to social accounts from the dashboard.
- X/Twitter, Instagram, TikTok, YouTube, Bluesky
- Schedule posts for later
- Bulk post across multiple businesses
- Post history and analytics

### 3. Business Dashboard
Unified view of all businesses at a glance.
- Per-business status cards
- Credential health checks
- Social account connection status
- Recent posts and engagement
- Quick actions (post, reconcile, configure)

### 4. Operations Center
Manage everything from one place.
- Add/remove businesses
- Configure social accounts per business
- Set up posting schedules
- View audit trail

## Architecture

```
Business Operations Center
├── Dashboard (HTML/JS)
├── REST API (FastAPI)
│   ├── /api/businesses          ← CRUD businesses
│   ├── /api/credentials         ← vault per business
│   ├── /api/social              ← social account management
│   ├── /api/posting             ← create/schedule posts
│   ├── /api/reconcile           ← reconciliation (existing)
│   └── /api/analytics           ← engagement metrics
├── Credential Vault (encrypted SQLite)
├── Social Publisher (API adapters)
├── Posting Scheduler (background)
└── Reconciliation Engine (existing)
```

## Database Tables

```sql
businesses (id, slug, name, domain, passport, created_at)
credentials (id, business_id, platform, key, value_encrypted, created_at)
social_accounts (id, business_id, platform, handle, status, connected_at)
posts (id, business_id, platform, content, media_urls, scheduled_at, posted_at, status)
reconciliation_runs (existing run_logs table)
```

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | /api/businesses | List all businesses |
| POST | /api/businesses | Add new business |
| GET | /api/businesses/{slug} | Get business detail |
| PATCH | /api/businesses/{slug} | Update business |
| DELETE | /api/businesses/{slug} | Remove business |
| GET | /api/credentials/{slug} | List credentials for business |
| POST | /api/credentials/{slug} | Add credential |
| DELETE | /api/credentials/{slug}/{key} | Remove credential |
| GET | /api/social/{slug} | List social accounts |
| POST | /api/social/{slug} | Connect social account |
| DELETE | /api/social/{slug}/{platform} | Disconnect social |
| POST | /api/posting/{slug} | Create post |
| GET | /api/posting/{slug} | List posts |
| POST | /api/posting/{slug}/schedule | Schedule post |
| POST | /api/analytics/{slug} | Get engagement data |
| POST | /api/reconcile | Run reconciliation |
| GET | /api/audit | View audit trail |
