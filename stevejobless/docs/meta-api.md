# Meta (Facebook) Graph API Documentation

Base URL: `https://graph.facebook.com/v21.0`

Authentication: `Authorization: Bearer <ACCESS_TOKEN>` or `?access_token=<ACCESS_TOKEN>`

## Getting Started

1. Create a Facebook App at developers.facebook.com
2. Get a Page Access Token (for page operations)
3. Use the Graph API Explorer to test endpoints
4. Reference: https://developers.facebook.com/docs/graph-api

---

## Pages

### Get Page Details

```
GET /{page-id}
```

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| fields | string | Comma-separated fields |
| access_token | string | Page access token |

#### Example

```bash
curl "https://graph.facebook.com/v21.0/PAGE_ID?fields=id,name,category,followers_count,access_token&access_token=PAGE_TOKEN"
```

#### Response

```json
{
  "id": "123456789",
  "name": "My Page",
  "category": "Technology",
  "followers_count": 15000,
  "access_token": "..."
}
```

### List Pages

```
GET /me/accounts
```

Returns pages managed by the authenticated user.

```bash
curl "https://graph.facebook.com/v21.0/me/accounts?fields=id,name,category,access_token&access_token=USER_TOKEN"
```

---

## Posts

### Get Page Posts

```
GET /{page-id}/posts
```

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| fields | string | Comma-separated fields |
| limit | integer | Results per page (1-100) |
| since | string | Unix timestamp for start |
| until | string | Unix timestamp for end |
| access_token | string | Page access token |

#### Example

```bash
curl "https://graph.facebook.com/v21.0/PAGE_ID/posts?fields=id,message,created_time,likes.summary(true),comments.summary(true)&limit=25&access_token=PAGE_TOKEN"
```

#### Response

```json
{
  "data": [
    {
      "id": "123456789_987654321",
      "message": "Hello World! This is a test post.",
      "created_time": "2026-09-01T12:00:00+0000",
      "likes": {"data": [], "summary": {"total_count": 42}},
      "comments": {"data": [], "summary": {"total_count": 5}}
    }
  ],
  "paging": {
    "cursors": {
      "before": "QVFIU...",
      "after": "QVFIU..."
    }
  }
}
```

### Create a Post

```
POST /{page-id}/feed
```

#### Body Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| message | string | Post text |
| link | string | URL to share |
| name | string | Name for the link |
| description | string | Description for the link |
| picture | string | URL of a picture |
| published | boolean | Publish immediately (default true) |
| scheduled_publish_time | integer | Unix timestamp for scheduled post |

#### Example - Text Post

```bash
curl -X POST "https://graph.facebook.com/v21.0/PAGE_ID/feed" \
  -d "message=Hello from the Graph API!" \
  -d "access_token=PAGE_TOKEN"
```

#### Example - Link Post

```bash
curl -X POST "https://graph.facebook.com/v21.0/PAGE_ID/feed" \
  -d "message=Check out this article!" \
  -d "link=https://example.com/article" \
  -d "name=Article Title" \
  -d "description=A great article about..." \
  -d "access_token=PAGE_TOKEN"
```

### Delete a Post

```
DELETE /{post-id}
```

```bash
curl -X DELETE "https://graph.facebook.com/v21.0/POST_ID?access_token=PAGE_TOKEN"
```

---

## Photos

### Upload a Photo

```
POST /{page-id}/photos
```

#### Body Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| message | string | Photo caption |
| source | file | Photo file (multipart form) |
| url | string | URL of photo to upload |
| published | boolean | Publish immediately |

#### Example - Upload from URL

```bash
curl -X POST "https://graph.facebook.com/v21.0/PAGE_ID/photos" \
  -d "message=Beautiful sunset!" \
  -d "url=https://example.com/sunset.jpg" \
  -d "access_token=PAGE_TOKEN"
```

### Get Photos

```
GET /{page-id}/photos
```

---

## Videos

### Upload a Video

```
POST /{page-id}/videos
```

#### Body Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| title | string | Video title |
| description | string | Video description |
| source | file | Video file (multipart form) |
| privacy | object | Privacy settings |

#### Example

```bash
curl -X POST "https://graph.facebook.com/v21.0/PAGE_ID/videos" \
  -F "source=@/path/to/video.mp4" \
  -F "title=My Video" \
  -F "description=Video description" \
  -F "access_token=PAGE_TOKEN"
```

---

## Comments

### Get Comments

```
GET /{post-id}/comments
```

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| fields | string | Comma-separated fields |
| limit | integer | Results per page |
| order | string | `chronological` or `reverse_chronological` |

### Post a Comment

```
POST /{post-id}/comments
```

```bash
curl -X POST "https://graph.facebook.com/v21.0/POST_ID/comments" \
  -d "message=Great post!" \
  -d "access_token=PAGE_TOKEN"
```

---

## Likes

### Like a Post

```
POST /{post-id}/likes
```

```bash
curl -X POST "https://graph.facebook.com/v21.0/POST_ID/likes" \
  -d "access_token=PAGE_TOKEN"
```

### Unlike a Post

```
DELETE /{post-id}/likes
```

---

## Insights (Analytics)

### Get Page Insights

```
GET /{page-id}/insights
```

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| metric | string | Comma-separated metrics |
| period | string | `day`, `week`, `28days`, `lifetime` |
| date_preset | string | `today`, `yesterday`, `last_month`, etc. |

#### Common Metrics

| Metric | Description |
|--------|-------------|
| `page_impressions` | Total impressions |
| `page_engaged_users` | Users who engaged |
| `page_post_engagements` | Post engagements |
| `page_views_total` | Total page views |
| `page_fan_adds` | New fans |
| `page_fan_removes` | Lost fans |

#### Example

```bash
curl "https://graph.facebook.com/v21.0/PAGE_ID/insights?metric=page_impressions,page_engaged_users&period=day&access_token=PAGE_TOKEN"
```

---

## Webhooks

### Verify Webhook

When setting up a webhook, Facebook sends a verification request:

```
GET /webhook?hub.mode=subscribe&hub.challenge=CHALLENGE_ARG&hub.verify_token=VERIFY_TOKEN
```

Return `CHALLENGE_ARG` if verify_token matches.

### Webhook Payload

```json
{
  "object": "page",
  "entry": [
    {
      "id": "PAGE_ID",
      "time": 1234567890,
      "changes": [
        {
          "field": "feed",
          "value": {
            "item": "status",
            "verb": "add",
            "post_id": "POST_ID",
            "message": "Hello!"
          }
        }
      ]
    }
  ]
}
```

---

## User Permissions

### Required Permissions

| Permission | Description |
|------------|-------------|
| `pages_show_list` | List managed pages |
| `pages_read_engagement` | Read page engagement data |
| `pages_manage_posts` | Create/delete posts |
| `pages_read_user_content` | Read user content on page |

---

## Error Response

```json
{
  "error": {
    "message": "Invalid OAuth access token.",
    "type": "OAuthException",
    "code": 190,
    "error_subcode": 102,
    "fbtrace_id": "..."
  }
}
```

### Common Error Codes

| Code | Description |
|------|-------------|
| 1 | API session expired |
| 2 | Service temporarily unavailable |
| 190 | Invalid OAuth access token |
| 200 | Permissions error |
| 368 | Rate limit reached |

---

## Rate Limits

- **Standard API calls:** 200 calls per hour per user
- **Business API:** Higher limits available
- **Ads API:** Separate rate limits

Check rate limit headers:
```
x-app-usage: {"call_count": 1, "total_cputime": 1, "total_time": 1}
```

---

## Pagination

Use cursor-based pagination:

```json
{
  "data": [...],
  "paging": {
    "cursors": {
      "before": "QVFI...",
      "after": "QVFI..."
    },
    "next": "https://graph.facebook.com/v21.0/...",
    "previous": "https://graph.facebook.com/v21.0/..."
  }
}
```

Include `after` cursor in next request:
```
GET /{page-id}/posts?after=CURSOR
```
