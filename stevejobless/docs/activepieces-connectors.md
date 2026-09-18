# Activepieces — Integration Platform Connector API

**Website:** https://www.activepieces.com
**Docs:** https://www.activepieces.com/docs/endpoints/connections/list

Open-source automation platform with 379+ pre-built integrations (pieces). Manage app connections and OAuth integrations programmatically.

## Base Endpoint

```
GET    /api/v1/app-connections
POST   /api/v1/app-connections
POST   /api/v1/app-connections/:id
DELETE /api/v1/app-connections/:id
GET    /api/v1/app-connections/owners
POST   /api/v1/app-connections/replace
```

## List Connections

```bash
GET /api/v1/app-connections?projectId=project_123&status=ACTIVE
```

**Query Parameters:**
- `pieceName`: Filter by piece name (e.g., `@activepieces/piece-slack`)
- `displayName`: Search by display name
- `status`: Filter by `ACTIVE`, `MISSING`, `ERROR`
- `scope`: Filter by `PROJECT` or `PLATFORM`
- `limit`: Number of results (1-100)
- `cursor`: Pagination cursor

## Create/Update Connection (Upsert)

```bash
POST /api/v1/app-connections
{
  "displayName": "My Slack Workspace",
  "pieceName": "@activepieces/piece-slack",
  "pieceVersion": "0.10.0",
  "type": "SECRET_TEXT",
  "externalId": "ext_slack_main",
  "value": {
    "type": "SECRET_TEXT",
    "secret_text": "xoxb-your-slack-token"
  }
}
```

## Connection Types

| Type | Description |
|------|-------------|
| `OAUTH2` | Self-managed OAuth with own credentials |
| `PLATFORM_OAUTH2` | Platform-level OAuth credentials |
| `CLOUD_OAUTH2` | Activepieces Cloud OAuth (simplest) |
| `SECRET_TEXT` | API keys, bearer tokens |
| `BASIC_AUTH` | Username/password |
| `CUSTOM_AUTH` | Flexible key-value pairs |
| `NO_AUTH` | Public APIs |

## Connection Status

| Status | Description |
|--------|-------------|
| `ACTIVE` | Connection is valid and working |
| `MISSING` | Connection deleted but still referenced |
| `ERROR` | Authentication errors (e.g., expired token) |

## Scope

- **PROJECT**: Available only in specified projects
- **PLATFORM**: Shared across multiple projects, managed by admins

## OAuth2 Flow

1. Redirect user to provider's authorization URL
2. User grants permissions
3. Receive callback with authorization code
4. Exchange code for access token
5. Store connection via API with tokens

## Embed SDK

```html
<script>
activepieces.connect({pieceName:'@activepieces/piece-google-sheets'});
</script>
```

**Connect Result:**
```json
{
  "connection": {
    "id": "conn_abc123",
    "name": "external-id"
  }
}
```

## Predefined Connections

For multi-tenant SaaS, create global connections via API:

```javascript
await createGlobalConnection({
  projectId,
  externalProjectId,
  apiKey,
  instanceUrl,
  pieceName,
  props,
  pieceAuthType
});
```

Set `requireAuth: false` in piece definitions to use predefined connections.
