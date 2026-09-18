# Domain Intelligence Engine API

## Base URL

```
https://domainnamechecker.dev
```

## Endpoints

### GET /api/health

Health check. Returns status, version, and available tools.

**Response:**

```json
{
  "status": "healthy",
  "version": "3.0.0",
  "tools": ["verify_domain", "generate_domains", "score_domain", "compare_registrars", "mine_domains", "get_analytics"]
}
```

### GET /api/verify/:domain

Full verification pipeline: DNS probe + RDAP registration check.

**Response:**

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

Status values: `available`, `taken`, `unknown`
Confidence: 0.0–1.0

### GET /api/registrar/:domain

Compare domain prices across registrars.

**Response:**

```json
{
  "domain": "example.com",
  "quotes": [
    { "registrar": "cloudflare", "registration": 8.57, "renewal": 8.57, "privacy": 0, "total_5_year": 42.85 },
    { "registrar": "porkbun", "registration": 8.58, "renewal": 9.25, "privacy": 0, "total_5_year": 45.58 }
  ],
  "best_year_1": { "registrar": "cloudflare" },
  "best_5_year": { "registrar": "cloudflare" },
  "checked_at": "2026-08-21T12:00:00Z"
}
```

### POST /api/mine

Full pipeline: generate + verify + score + compare. Checks top 20 candidates.

**Request:**

```json
{
  "concept": "tiny api tools",
  "intent": "get",
  "tlds": ["com"]
}
```

**Response:**

```json
{
  "concept": "tiny api tools",
  "intent": "get",
  "results": [
    {
      "domain": "tinyget.com",
      "score": 14,
      "meaning": { "meaning": "tinyget", "strength": "weak" },
      "registrar": { "registrar": "cloudflare", "total_5_year": 42.85 }
    }
  ]
}
```

### POST /mcp

MCP endpoint. Supports `tools/list` and `tools/call` JSON-RPC methods.

See [MCP documentation](/docs/mcp.md) for tool definitions.
