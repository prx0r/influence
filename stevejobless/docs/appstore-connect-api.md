# App Store Connect API Documentation

Base URL: `https://api.appstoreconnect.apple.com/v1`

Authentication: JSON Web Tokens (JWT) signed with your API key

## Getting Started

1. The Account Holder must request access to the API in App Store Connect
2. Generate a team API key or individual API key
3. Download the private key file (.p8)
4. Create JWTs to authenticate requests

### Creating JWTs

Header:
```json
{
  "alg": "ES256",
  "typ": "JWT",
  "kid": "YOUR_KEY_ID"
}
```

Payload:
```json
{
  "iss": "YOUR_ISSUER_ID",
  "iat": 1234567890,
  "exp": 1234567890,
  "aud": "appstoreconnect-v1"
}
```

Sign with your private key using ES256 (P-256 + SHA-256).

### Example Request

```bash
curl -X GET "https://api.appstoreconnect.apple.com/v1/apps" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

---

## Apps

### List Apps

```
GET /apps
```

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| filter[name] | string | Filter by app name |
| filter[bundleId] | string | Filter by bundle ID |
| filter[sku] | string | Filter by SKU |
| sort | string | `name`, `-name`, `sku`, `-sku` |
| limit | integer | 1-200 (default 20) |
| include | string | Related resources to include |
| fields[apps] | string | Fields to return |

#### Example

```bash
curl "https://api.appstoreconnect.apple.com/v1/apps?filter[name]=MyApp&limit=10" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

#### Response

```json
{
  "data": [
    {
      "type": "apps",
      "id": "123456789",
      "attributes": {
        "name": "MyApp",
        "bundleId": "com.company.myapp",
        "sku": "com.company.myapp",
        "primaryLocale": "en-US",
        "availableInNewTerritories": true,
        "contentRightsDeclaration": "DOES_NOT_USE_THIRD_PARTY_CONTENT"
      },
      "links": {
        "self": "https://api.appstoreconnect.apple.com/v1/apps/123456789"
      },
      "relationships": {
        "appStoreVersions": {
          "links": {
            "self": "https://api.appstoreconnect.apple.com/v1/apps/123456789/relationships/appStoreVersions",
            "related": "https://api.appstoreconnect.apple.com/v1/apps/123456789/appStoreVersions"
          }
        },
        "builds": {
          "links": {
            "self": "https://api.appstoreconnect.apple.com/v1/apps/123456789/relationships/builds",
            "related": "https://api.appstoreconnect.apple.com/v1/apps/123456789/builds"
          }
        }
      }
    }
  ]
}
```

### Get App Details

```
GET /apps/{id}
```

### Modify an App

```
PATCH /apps/{id}
```

#### Body Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| data.attributes.availableInNewTerritories | boolean | Availability |
| data.attributes.contentRightsDeclaration | string | Content rights |

#### Example

```bash
curl -X PATCH "https://api.appstoreconnect.apple.com/v1/apps/123456789" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "type": "apps",
      "id": "123456789",
      "attributes": {
        "availableInNewTerritories": true,
        "contentRightsDeclaration": "DOES_NOT_USE_THIRD_PARTY_CONTENT"
      }
    }
  }'
```

---

## Builds

### List Builds

```
GET /builds
```

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| filter[app] | string | Filter by app ID |
| filter[expired] | boolean | Filter by expiration |
| filter[processingState] | string | `PROCESSING`, `FAILED`, `INVALID`, `VALID` |
| sort | string | `uploadedDate`, `-uploadedDate` |
| limit | integer | 1-200 |

### Get Build Details

```
GET /builds/{id}
```

### Upload Build

Builds are uploaded via Xcode or `xcrun notarytool`, not directly via REST API.

---

## App Store Versions

### List Versions

```
GET /apps/{id}/appStoreVersions
```

### Create Version

```
POST /appStoreVersions
```

### Submit for Review

```
POST /appStoreVersionSubmissions
```

---

## TestFlight

### List Beta Groups

```
GET /apps/{id}/betaGroups
```

### Add Beta Testers

```
POST /betaTesterInvitations
```

### List Beta Builds

```
GET /apps/{id}/preReleaseVersions
```

---

## In-App Purchases

### List In-App Purchases

```
GET /apps/{id}/inAppPurchases
```

### Create In-App Purchase

```
POST /inAppPurchases
```

---

## Subscriptions

### List Subscription Groups

```
GET /apps/{id}/subscriptionGroups
```

### Create Subscription

```
POST /subscriptions
```

---

## Customer Reviews

### List Reviews

```
GET /apps/{id}/customerReviews
```

### Respond to Review

```
POST /customerReviewResponses
```

---

## Provisioning

### Bundle IDs

```
GET /bundleIds
POST /bundleIds
```

### Certificates

```
GET /certificates
POST /certificates
```

### Devices

```
GET /devices
POST /devices
```

### Profiles

```
GET /profiles
POST /profiles
```

---

## Reporting

### Sales Reports

```
GET /salesReports
```

### Download Financial Reports

```
GET /financeReports
```

---

## Users and Access

### List Users

```
GET /users
```

### Invite User

```
POST /invitations
```

---

## Xcode Cloud

### List Workflows

```
GET /ciProducts/{id}/workflows
```

### List Builds

```
GET /ciProducts/{id}/builds
```

### Start Build

```
POST /ciBuildRuns
```

---

## Webhooks

### List Webhooks

```
GET /webhooks
```

### Create Webhook

```
POST /webhooks
```

#### Body

```json
{
  "data": {
    "type": "webhooks",
    "attributes": {
      "url": "https://your-server.com/webhook",
      "events": ["APP_STORE_VERSION_STATE_CHANGED", "RESOURCE_STATE_CHANGED"]
    }
  }
}
```

---

## Response Format

All responses follow JSON:API specification:

```json
{
  "data": {...},
  "included": [...],
  "links": {
    "self": "...",
    "first": "...",
    "next": "...",
    "prev": "..."
  },
  "meta": {
    "paging": {
      "total": 100,
      "limit": 20
    }
  }
}
```

## Error Format

```json
{
  "errors": [
    {
      "id": "unique-error-id",
      "status": "409",
      "code": "ENTITY_ERROR.ATTRIBUTE.INVALID.DUPLICATE",
      "title": "The given attribute value is invalid",
      "detail": "An app with bundle ID 'com.company.app' already exists",
      "source": {
        "pointer": "/data/attributes/bundleId"
      }
    }
  ]
}
```

### Common Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad request |
| 401 | Unauthorized (invalid JWT) |
| 403 | Forbidden (insufficient permissions) |
| 404 | Resource not found |
| 409 | Conflict (duplicate resource) |
| 422 | Unprocessable entity (validation error) |
| 429 | Rate limit exceeded |

## Rate Limits

- **Standard:** 3,600 requests per hour per key
- **Burst:** 60 requests per second

---

## Resource Types

| Resource | Description |
|----------|-------------|
| `apps` | App information |
| `builds` | Uploaded builds |
| `appStoreVersions` | App Store versions |
| `betaGroups` | TestFlight groups |
| `betaTesters` | Beta testers |
| `inAppPurchases` | In-app purchases |
| `subscriptionGroups` | Subscription groups |
| `subscriptions` | Subscriptions |
| `customerReviews` | Customer reviews |
| `certificates` | Signing certificates |
| `devices` | Registered devices |
| `profiles` | Provisioning profiles |
| `bundleIds` | Bundle identifiers |
| `users` | Team users |
