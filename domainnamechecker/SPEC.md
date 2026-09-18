# DomainNameChecker Spec

## V1 — Working Verification + Cheapest Registrar Links

**Goal**: Fully working domain verification with authoritative RDAP checks and working links to buy at the cheapest registrar.

### Core Features (Implemented)
- **DNS + RDAP verification** — Authoritative registration status via RDAP, DNS fallback
- **Registrar price comparison** — Cloudflare, Porkbun, Dynadot, Namecheap with 5-year cost projections
- **Buy links** — Direct links to purchase at each registrar
- **Bulk verify** — Check up to 50 domains at once via POST /api/bulk-verify
- **Input validation** — Domain format validation on all endpoints
- **MCP server** — 6 tools for AI agent integration
- **Streaming search** — SSE endpoint for real-time domain discovery
- **Landing page** — Clean UI with search, pricing, and buy links

### API Endpoints
```
GET  /api/verify/:domain      — Verify domain (DNS + RDAP)
GET  /api/registrar/:domain   — Compare registrar prices
POST /api/mine                — Full pipeline: generate + verify + score + compare
POST /api/bulk-verify         — Check up to 50 domains at once
POST /api/search              — Streaming search via SSE
POST /mcp                     — MCP endpoint (JSON-RPC)
GET  /api/health              — Health check
```

### Bug Fixes Applied
1. Fixed Cloudflare buy link (was broken, now points to registrar page)
2. Added input validation with `validateDomain()` function
3. Added `decodeURIComponent` to URL path extraction
4. Fixed Chinese comment in source code
5. Fixed landing page canonical URL (was workers.dev, now custom domain)
6. Added proper HTTP 400 responses for invalid inputs
7. Updated health endpoint to list all available endpoints
8. Version bumped to 3.1.0

### Deployment
```bash
cd worker
wrangler deploy
```

### Remaining V1 Work
- [ ] Add R2 caching for verification results (requires wrangler R2 binding)
- [ ] Update Rust CLI to match Worker capabilities (RDAP, scoring, registrar comparison)
- [ ] Add rate limiting (Cloudflare WAF or Worker middleware)
- [ ] Add CORS headers for custom domain

---

## V2 — Domain Intelligence with Smart Suggestions

**Goal**: AI-powered domain name intelligence with contextual suggestions, semantic analysis, and availability alerts.

### Planned Features
- **Smart suggestions** — LLM-powered domain name generation based on context, style, and intent
- **Semantic analysis** — Deeper meaning scoring with phonosemantic analysis
- **Domain history** — Track availability changes over time via R2 storage
- **Price alerts** — Notify when domains become available or prices drop
- **Bulk mining** — Generate + verify + score 100+ candidates in parallel
- **Export** — CSV/JSON export of domain analysis results
- **Domain portfolio** — Save and manage domains of interest
- **API key auth** — Rate limiting and usage tracking per API key

### Research Foundation
- NAMING_SCIENCE.md — 761-line treatise on domain naming science
- DOMAIN_ANIMAL_SCIENCE.md — Research on animal metaphor domains
- Bradley-Terry preference modeling for domain selection
- Phonosemantic analysis for name meaning strength

### Architecture
- **Worker** — Primary API and UI (Cloudflare Workers)
- **R2** — Domain check history and caching
- **D1** — Structured data for domain portfolio and price alerts (future)
- **Rust CLI** — Local tool for batch operations
