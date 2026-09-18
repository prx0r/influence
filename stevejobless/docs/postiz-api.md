# Postiz Public API Documentation

Base URL: `https://api.postiz.com/public/v1` (Cloud) or `https://{your-domain}/api/public/v1` (Self-hosted)

Authentication: `Authorization: <API_KEY>` or `Authorization: pos_<OAUTH_TOKEN>`

Rate Limits: 90 requests per hour (100 for cloud) on create-post endpoint

## Supported Platforms (32 total)

| Platform | `__type` | Key Settings |
|----------|----------|--------------|
| X (Twitter) | `x` | `who_can_reply_post`, `community` |
| LinkedIn | `linkedin` | `post_as_images_carousel` |
| LinkedIn Page | `linkedin-page` | `post_as_images_carousel` |
| Facebook | `facebook` | `url` (optional) |
| Instagram (FB-linked) | `instagram` | `post_type`, `collaborators` |
| Instagram Standalone | `instagram-standalone` | `post_type`, `collaborators` |
| YouTube | `youtube` | `title`, `type` |
| TikTok | `tiktok` | `privacy_level`, `duet`, `stitch`, `comment`, `content_posting_method` |
| Reddit | `reddit` | `subreddit[]` |
| Discord | `discord` | `channel` |
| Slack | `slack` | `channel` |
| Pinterest | `pinterest` | `board`, `title` |
| Medium | `medium` | `title`, `subtitle`, `tags` |
| Threads | `threads` | (none) |
| Bluesky | `bluesky` | (none) |
| Mastodon | `mastodon` | (none) |
| Telegram | `telegram` | (none) |

---

## Integrations (Channels)

### List Integrations

```
GET /integrations
```

Returns all connected social media channels for your organization.

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| group | string | Filter by customer/group ID |

#### Example

```bash
curl "https://api.postiz.com/public/v1/integrations" \
  -H "Authorization: YOUR_API_KEY"
```

#### Response

```json
[
  {
    "id": "cm4ean69r0003w8w1cdomox9n",
    "name": "Nevo David",
    "identifier": "x",
    "picture": "https://uploads.postiz.com/avatar.jpg",
    "disabled": false,
    "profile": "nevodavid",
    "customer": {
      "id": "customer-id",
      "name": "My Company"
    }
  }
]
```

### Get OAuth URL for Channel

```
GET /social/{integration}
```

Generate an OAuth authorization URL for a given integration.

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| integration | string (path) | Platform identifier (e.g., `x`, `linkedin`, `facebook`) |
| refresh | string (query) | Existing integration ID to refresh OAuth token |

#### Example

```bash
curl "https://api.postiz.com/public/v1/social/x" \
  -H "Authorization: YOUR_API_KEY"
```

#### Response

```json
{
  "url": "https://twitter.com/i/oauth2/authorize?response_type=code&client_id=..."
}
```

### Delete a Channel

```
DELETE /integrations/{id}
```

```bash
curl -X DELETE "https://api.postiz.com/public/v1/integrations/INTEGRATION_ID" \
  -H "Authorization: YOUR_API_KEY"
```

---

## Groups (Customers)

### List Groups

```
GET /groups
```

```bash
curl "https://api.postiz.com/public/v1/groups" \
  -H "Authorization: YOUR_API_KEY"
```

#### Response

```json
[
  {
    "id": "customer-id",
    "name": "My Company"
  }
]
```

---

## Posts

### Create Post

```
POST /posts
```

#### Body Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| type | string | yes | `now`, `schedule`, or `draft` |
| date | string | yes | ISO 8601 publish date (ignored for `now`) |
| shortLink | boolean | yes | Use short links |
| tags | array | yes | Array of tags |
| posts | array | yes* | Array of post items |

*Required if type is not `draft`

#### Post Item Structure

| Parameter | Type | Description |
|-----------|------|-------------|
| integration.id | string (required) | Integration ID |
| value | array (required) | Array of content objects |
| settings | object | Platform-specific settings |

#### Content Object

| Parameter | Type | Description |
|-----------|------|-------------|
| content | string (required) | Post text |
| image | array | Array of media objects |

#### Example - Schedule a post to X (Twitter)

```json
{
  "type": "schedule",
  "date": "2024-12-14T10:00:00.000Z",
  "shortLink": false,
  "tags": [],
  "posts": [
    {
      "integration": { "id": "your-x-integration-id" },
      "value": [
        {
          "content": "Hello from the Postiz API!",
          "image": []
        }
      ],
      "settings": {
        "__type": "x",
        "who_can_reply_post": "everyone"
      }
    }
  ]
}
```

#### Example - Post immediately to LinkedIn

```json
{
  "type": "now",
  "date": "2024-12-14T10:00:00.000Z",
  "shortLink": false,
  "tags": [],
  "posts": [
    {
      "integration": { "id": "your-linkedin-id" },
      "value": [
        {
          "content": "Exciting announcement!",
          "image": []
        }
      ],
      "settings": {
        "__type": "linkedin"
      }
    }
  ]
}
```

#### Example - YouTube Video

```json
{
  "type": "schedule",
  "date": "2024-12-14T10:00:00.000Z",
  "shortLink": false,
  "tags": [],
  "posts": [
    {
      "integration": { "id": "your-youtube-id" },
      "value": [
        {
          "content": "Video description here...",
          "image": [{ "id": "video-id", "path": "https://uploads.postiz.com/video.mp4" }]
        }
      ],
      "settings": {
        "__type": "youtube",
        "title": "My Awesome Video",
        "type": "public"
      }
    }
  ]
}
```

#### Example - TikTok Post

```json
{
  "type": "schedule",
  "date": "2024-12-14T10:00:00.000Z",
  "shortLink": false,
  "tags": [],
  "posts": [
    {
      "integration": { "id": "your-tiktok-id" },
      "value": [
        {
          "content": "Check this out! #viral #fyp",
          "image": [{ "id": "video-id", "path": "https://uploads.postiz.com/tiktok.mp4" }]
        }
      ],
      "settings": {
        "__type": "tiktok",
        "privacy_level": "PUBLIC_TO_EVERYONE",
        "duet": true,
        "stitch": true,
        "comment": true,
        "autoAddMusic": "no",
        "brand_content_toggle": false,
        "brand_organic_toggle": false,
        "content_posting_method": "DIRECT_POST"
      }
    }
  ]
}
```

#### Post Types

| Type | Description |
|------|-------------|
| `now` | Publish immediately |
| `schedule` | Publish at the time given in `date` |
| `draft` | Save as draft (not published) |

---

### List Posts

```
GET /posts
```

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| startDate | string | yes | Start date (ISO 8601) |
| endDate | string | yes | End date (ISO 8601) |
| customer | string | no | Filter by customer ID |

#### Example

```bash
curl "https://api.postiz.com/public/v1/posts?startDate=2024-12-01T00:00:00.000Z&endDate=2024-12-31T23:59:59.000Z" \
  -H "Authorization: YOUR_API_KEY"
```

#### Response

```json
{
  "posts": [
    {
      "id": "post-123",
      "content": "Hello World!",
      "settings": {"content_posting_method": "DIRECT_POST"},
      "publishDate": "2024-12-14T10:00:00.000Z",
      "releaseURL": "https://x.com/user/status/123456",
      "state": "PUBLISHED",
      "integration": {
        "id": "integration-456",
        "providerIdentifier": "x",
        "name": "My X Account",
        "picture": "https://..."
      }
    }
  ]
}
```

#### Post States

| State | Description |
|-------|-------------|
| `QUEUE` | Scheduled and waiting |
| `PUBLISHED` | Successfully published |
| `ERROR` | Publishing failed |
| `DRAFT` | Saved as draft |

---

### Delete Post

```
DELETE /posts/{id}
```

```bash
curl -X DELETE "https://api.postiz.com/public/v1/posts/POST_ID" \
  -H "Authorization: YOUR_API_KEY"
```

---

## Uploads

### Upload Media

```
POST /upload
```

#### Request

```bash
curl -X POST "https://api.postiz.com/public/v1/upload" \
  -H "Authorization: YOUR_API_KEY" \
  -F "file=@photo.jpg"
```

#### Response

```json
{
  "id": "img-123",
  "path": "https://uploads.postiz.com/photo.jpg"
}
```

Use the returned `id` and `path` in post creation:

```json
{
  "content": "Beautiful sunset!",
  "image": [{"id": "img-123", "path": "https://uploads.postiz.com/photo.jpg"}]
}
```

---

## Analytics

### Get Integration Analytics

```
GET /analytics/{integrationId}
```

### Get Post Analytics

```
GET /analytics/posts/{postId}
```

---

## Notifications

### List Notifications

```
GET /notifications
```

---

## Platform-Specific Settings

### X (Twitter) Settings

```json
{
  "__type": "x",
  "who_can_reply_post": "everyone|following|mentionedUsers|subscribers|verified",
  "community": "https://x.com/i/communities/123"
}
```

### LinkedIn Settings

```json
{
  "__type": "linkedin",
  "post_as_images_carousel": false
}
```

### Instagram Settings

```json
{
  "__type": "instagram",
  "post_type": "post|story",
  "collaborators": [{"label": "username"}]
}
```

### YouTube Settings

```json
{
  "__type": "youtube",
  "title": "Video Title",
  "type": "public|private|unlisted",
  "selfDeclaredMadeForKids": "yes|no",
  "tags": [{"value": "tag", "label": "Tag"}]
}
```

### TikTok Settings

```json
{
  "__type": "tiktok",
  "privacy_level": "PUBLIC_TO_EVERYONE|MUTUAL_FOLLOW_FRIENDS|FOLLOWER_OF_CREATOR|SELF_ONLY",
  "duet": true,
  "stitch": true,
  "comment": true,
  "autoAddMusic": "yes|no",
  "brand_content_toggle": false,
  "brand_organic_toggle": false,
  "video_made_with_ai": false,
  "content_posting_method": "DIRECT_POST|UPLOAD"
}
```

### Reddit Settings

```json
{
  "__type": "reddit",
  "subreddit": [
    {
      "value": {
        "subreddit": "programming",
        "title": "Post Title",
        "type": "self|link|image|video",
        "url": "",
        "is_flair_required": false
      }
    }
  ]
}
```

---

## Error Responses

| Status | Meaning |
|--------|---------|
| 400 | Bad request (malformed body) |
| 401 | Unauthorized (missing/invalid API key) |
| 403 | Forbidden (key doesn't own resource) |
| 404 | Not found |
| 413 | Payload too large (>50MB) |
| 429 | Rate limit exceeded |
| 5xx | Server error |

For DELETE endpoints, 404 means "already deleted" and is safe to ignore.

---

## SDKs

- **Node.js SDK:** `npm install @postiz/node`
- **n8n Node:** `npm install n8n-nodes-postiz`
