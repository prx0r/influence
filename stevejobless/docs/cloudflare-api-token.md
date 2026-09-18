# Cloudflare API Token Guide

**Docs:** https://developers.cloudflare.com/fundamentals/api/get-started/create-token/

## Create API Token

1. Log into Cloudflare dashboard
2. Go to **My Profile** → **API Tokens**
3. Click **Create Token**
4. Select a template or create custom token
5. Configure:
   - **Token name**: Describe usage
   - **Permissions**: Choose `Read` or `Edit` for each group
   - **Resources**: Select zones/accounts the token can access
6. Click **Continue to summary**
7. Review and click **Create Token**
8. Copy the secret immediately (shown only once)

## Token Format

New tokens use `cfut_` prefix (scannable format for credential scanning tools).

Account tokens use `cfat_` prefix.

## Verify Token

```bash
curl "https://api.cloudflare.com/client/v4/user/tokens/verify" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

## Create Tokens via API

```bash
curl "https://api.cloudflare.com/client/v4/user/tokens" \
  -H "Authorization: Bearer EXISTING_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "readonly token",
    "policies": [{
      "effect": "allow",
      "resources": {
        "com.cloudflare.api.account.zone.ZONE_ID": "*"
      },
      "permission_groups": [
        {"id": "c8fed203ed3043cba015a93ad1616f1f", "name": "Zone Read"},
        {"id": "82e64a83756745bbbb1c9c2701bf816b", "name": "DNS Read"}
      ]
    }],
    "not_before": "2024-01-01T00:00:00Z",
    "expires_on": "2024-12-31T23:59:59Z"
  }'
```

## Permission Groups

| Group | Access |
|-------|--------|
| Zone Read | Read zone settings |
| Zone Edit | Full zone management |
| DNS Read | Read DNS records |
| DNS Edit | Create/update/delete DNS |
| SSL Read | Read SSL settings |
| SSL Edit | Manage SSL |
| Workers Read | Read Workers |
| Workers Edit | Manage Workers |

## Restrictions

- **Client IP**: Restrict by CIDR notation
- **TTL**: Set `not_before` and `expires_on` (UTC timestamps)

## Account Tokens

1. Go to **Manage Account** → **Account API Tokens**
2. Requires Super Administrator permission
3. Tokens use `cfat_` prefix
