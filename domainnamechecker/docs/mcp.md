# Domain Intelligence Engine MCP Server

## Transport

Streamable HTTP POST to `/mcp`. Stateless — no session management.

```bash
curl -X POST https://domainnamechecker.dev/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

## Tools

### verify_domain

Full verification pipeline: DNS probe + RDAP registration check. Returns availability status with confidence score.

**Input:**

```json
{
  "domain": "example.com"
}
```

**Output:**

```json
{
  "domain": "example.com",
  "registration": {
    "status": "taken",
    "confidence": 0.99,
    "authoritative": true,
    "verified_at": "2026-08-21T12:00:00Z"
  },
  "evidence": [
    { "source": "dns", "status": "records_found" },
    { "source": "rdap", "status": "registered" }
  ],
  "dns": { "has_records": true, "records": { "A": ["93.184.216.34"] } },
  "rdap": { "registered": true, "name": "example.com" },
  "schema_version": "3.0.0"
}
```

### generate_domains

Generate domain candidates from a concept. Produces split variants, compounds with suffixes, and HTTP status code variants.

**Input:**

```json
{
  "concept": "tiny api tools",
  "tlds": ["com"]
}
```

**Output:**

```json
{
  "concept": "tiny api tools",
  "candidates": ["t-i-n-y.com", "tiny-api.com", "tinyapi.com", ...],
  "count": 150
}
```

### score_domain

Score a domain by semantic meaning, length, hyphens, TLD, and developer/agent relevance.

**Input:**

```json
{
  "domain": "tinyget.com",
  "intent": "get"
}
```

**Output:**

```json
{
  "domain": "tinyget.com",
  "intent": "get",
  "score": 14,
  "meaning": {
    "meaning": "tinyget",
    "strength": "weak",
    "developerNative": false,
    "agentNative": false
  }
}
```

### compare_registrars

Compare domain prices across Cloudflare, Porkbun, Dynadot, and Namecheap. Includes 5-year cost projections.

**Input:**

```json
{
  "domain": "example.com"
}
```

**Output:**

```json
{
  "domain": "example.com",
  "quotes": [
    { "registrar": "cloudflare", "registration": 8.57, "renewal": 8.57, "total_5_year": 42.85 }
  ],
  "best_year_1": { "registrar": "cloudflare" },
  "best_5_year": { "registrar": "cloudflare" }
}
```

### mine_domains

Full pipeline: generate candidates from concept, verify availability, score, compare registrars. Returns top 10 available domains sorted by score.

**Input:**

```json
{
  "concept": "tiny api tools",
  "intent": "get",
  "tlds": ["com"]
}
```

**Output:**

```json
{
  "concept": "tiny api tools",
  "intent": "get",
  "total_candidates": 150,
  "available": 3,
  "search_id": "search-1234567890",
  "results": [
    {
      "domain": "tinyget.com",
      "registration": { "status": "available", "confidence": 0.99 },
      "score": 14,
      "meaning": { ... },
      "registrar": { "registrar": "cloudflare", "total_5_year": 42.85 }
    }
  ]
}
```

### get_analytics

Get search and click analytics (in-memory, resets on worker restart).

**Input:**

```json
{}
```

**Output:**

```json
{
  "total_searches": 42,
  "total_clicks": 187,
  "top_domains": [["tinyget.com", 23], ["minitool.com", 15]]
}
```

## Annotations

All tools are read-only, non-destructive, idempotent, and open-world.
