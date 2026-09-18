# Cloudflare API Documentation

Base URL: `https://api.cloudflare.com/client/v4`

Authentication: `Authorization: Bearer <API_TOKEN>`

## Zones

### List Zones

```
GET /zones
```

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| name | string | Filter by zone name |
| status | string | `active`, `pending`, `initializing`, `moved`, `deleted`, `deactivation_pending`, `backorder_pending`, `migration_in_progress`, `migration_complete`, `migration_expired` |
| account.id | string | Filter by account ID |
| order | string | `name`, `status` |
| direction | `asc` or `desc` | Sort direction |
| match | string | `any` or `all` |

#### Example

```bash
curl "https://api.cloudflare.com/client/v4/zones" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN"
```

#### Response

```json
{
  "result": [
    {
      "id": "023e105f4ecef8ad9ca31a8372d0c353",
      "name": "example.com",
      "status": "active",
      "development_mode": 0,
      "name_servers": ["ns1.example.com", "ns2.example.com"],
      "original_name_servers": ["ns1.cloudflare.com", "ns2.cloudflare.com"],
      "created_on": "2014-01-01T05:20:00.12345Z",
      "modified_on": "2014-01-01T05:20:00.12345Z",
      "activated_on": "2014-01-01T05:20:00.12345Z",
      "account": {"id": "account-id", "name": "Account Name"},
      "meta": {"step": 1, "custom_certificate_quota": 0, "dns_quota": 1000, "phishing_detected": false},
      "owner": {"id": "owner-id", "email": "owner@example.com"},
      "plan": {"id": "plan-id", "name": "Pro", "price": 20, "currency": "USD"},
      "plan_pending_id": "plan-id",
      "status_desc": "Your zone is ready to use",
      "type": "full"
    }
  ],
  "result_info": {
    "page": 1,
    "per_page": 20,
    "count": 1,
    "total_count": 1
  }
}
```

### Get Zone Details

```
GET /zones/{zone_id}
```

### Create a Zone

```
POST /zones
```

### Edit a Zone

```
PATCH /zones/{zone_id}
```

### Delete a Zone

```
DELETE /zones/{zone_id}
```

---

## DNS Records

### List DNS Records

```
GET /zones/{zone_id}/dns_records
```

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| type | string | `A`, `AAAA`, `CNAME`, `TXT`, `SRV`, `LOC`, `MX`, `NS`, `SPF`, `CAA`, `CERT`, `DNSKEY`, `DS`, `HTTPS`, `NAPTR`, `SMIMEA`, `SSHFP`, `SVCB`, `TLSA`, `URI` |
| name | string | DNS record name |
| content | string | DNS record content |
| comment | string | Filter by comment |
| tag | string | Filter by tag |
| order | string | `type`, `name`, `content`, `ttl`, `proxied` |
| direction | `asc` or `desc` | Sort direction |
| match | string | `any` or `all` |
| per_page | integer | Results per page (100 default, 5000 max) |
| page | integer | Page number |
| search | string | Search term |

#### Example

```bash
curl "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN"
```

#### Response

```json
{
  "success": true,
  "result": [
    {
      "id": "023e105f4ecef8ad9ca31a8372d0c353",
      "name": "example.com",
      "ttl": 3600,
      "type": "A",
      "comment": "Domain verification record",
      "content": "198.51.100.4",
      "proxied": true,
      "created_on": "2014-01-01T05:20:00.12345Z",
      "modified_on": "2014-01-01T05:20:00.12345Z",
      "proxiable": true,
      "tags": ["owner:dns-team"]
    }
  ],
  "result_info": {
    "count": 1,
    "page": 1,
    "per_page": 20,
    "total_count": 2000,
    "total_pages": 100
  }
}
```

### Get DNS Record Details

```
GET /zones/{zone_id}/dns_records/{dns_record_id}
```

### Create a DNS Record

```
POST /zones/{zone_id}/dns_records
```

#### Body Parameters (A Record Example)

| Parameter | Type | Description |
|-----------|------|-------------|
| name | string (required) | Record name (e.g., "sub.example.com") |
| type | string (required) | Record type: `A`, `AAAA`, `CNAME`, `TXT`, `MX`, etc. |
| content | string (required) | Record content |
| ttl | integer | TTL in seconds (1 = automatic, 60-86400) |
| proxied | boolean | Enable Cloudflare proxy |
| comment | string | Comment for the record |
| tags | array | Array of tags |

#### Example - A Record

```bash
curl -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "sub.example.com",
    "type": "A",
    "content": "192.0.2.1",
    "ttl": 3600,
    "proxied": true,
    "comment": "My A record"
  }'
```

#### Example - CNAME Record

```bash
curl -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "www.example.com",
    "type": "CNAME",
    "content": "example.com",
    "ttl": 3600,
    "proxied": true
  }'
```

### Overwrite a DNS Record (PUT)

```
PUT /zones/{zone_id}/dns_records/{dns_record_id}
```

### Update a DNS Record (PATCH)

```
PATCH /zones/{zone_id}/dns_records/{dns_record_id}
```

### Delete a DNS Record

```
DELETE /zones/{zone_id}/dns_records/{dns_record_id}
```

```bash
curl -X DELETE "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records/$RECORD_ID" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN"
```

### Batch DNS Records

```
POST /zones/{zone_id}/dns_records/batch
```

### Export DNS Records

```
GET /zones/{zone_id}/dns_records/export
```

### Import DNS Records

```
POST /zones/{zone_id}/dns_records/import
```

---

## DNS Record Types

| Type | Description |
|------|-------------|
| `A` | Maps domain to IPv4 address |
| `AAAA` | Maps domain to IPv6 address |
| `CNAME` | Canonical name, points to another domain |
| `MX` | Mail exchange server |
| `TXT` | Text record (SPF, DKIM, verification) |
| `SRV` | Service locator |
| `NS` | Name server |
| `CAA` | Certification Authority Authorization |
| `PTR` | Reverse DNS lookup |
| `SOA` | Start of Authority |
| `DS` | Delegation Signer |
| `DNSKEY` | DNSSEC public key |

---

## Zone Settings

### Get Zone Settings

```
GET /zones/{zone_id}/settings
```

### Get Specific Setting

```
GET /zones/{zone_id}/settings/{setting_id}
```

### Edit Zone Setting

```
PATCH /zones/{zone_id}/settings/{setting_id}
```

---

## Error Response Format

```json
{
  "success": false,
  "errors": [
    {
      "code": 1000,
      "message": "message",
      "documentation_url": "https://...",
      "source": {"pointer": "pointer"}
    }
  ],
  "messages": []
}
```

## Common Error Codes

| Code | Description |
|------|-------------|
| 7000 | DNS record already exists |
| 7003 | Zone is not valid |
| 7023 | Authentication failed |
| 9106 | Missing or invalid API token |

## Pagination

Cloudflare uses cursor-based pagination. The `result_info` object contains:

```json
{
  "page": 1,
  "per_page": 100,
  "count": 100,
  "total_count": 2500,
  "total_pages": 25
}
```

Use `page` and `per_page` parameters to paginate.
