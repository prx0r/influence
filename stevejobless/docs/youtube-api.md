# YouTube Data API v3 Documentation

Base URL: `https://www.googleapis.com/youtube/v3`

Authentication: `Authorization: Bearer <OAUTH2_TOKEN>` or `key=<API_KEY>` for public data

## Getting Started

1. Create a Google Account
2. Create a project in Google Developers Console
3. Enable YouTube Data API v3
4. Obtain authorization credentials (OAuth 2.0)
5. Use client library or make API requests

## Key Concepts

### The `part` Parameter

Required for all resource requests. Identifies which resource properties to include in the response.

Example: `part=snippet,contentDetails,statistics`

### The `fields` Parameter

Filters the API response to only return specific properties.

Example: `fields=items(id,snippet(title,categoryId),statistics)`

### Quota

- Default: 10,000 units/day
- `search.list`: 100 units/day (default)
- `videos.insert`: 100 units/day (default)
- Most `list` operations: 1 unit per request
- Write operations: 50 units per request
- Video upload: 1,600 units

---

## Channels

### List Channels

```
GET /channels
```

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| part | string (required) | Comma-separated parts: `snippet`, `contentDetails`, `statistics`, `status`, `brandingSettings` |
| mine | boolean | List channels for authenticated user |
| forUsername | string | Channel for specific username |
| id | string | Comma-separated channel IDs |
| maxResults | integer | 0-50 (default 5) |

#### Example

```bash
curl "https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics&mine=true&key=$API_KEY" \
  -H "Authorization: Bearer $OAUTH_TOKEN"
```

#### Response

```json
{
  "kind": "youtube#channelListResponse",
  "etag": "...",
  "pageInfo": {
    "totalResults": 1,
    "resultsPerPage": 5
  },
  "items": [
    {
      "kind": "youtube#channel",
      "etag": "...",
      "id": "UC_x5XG1OV2P6uZZ5FSM9Ttw",
      "snippet": {
        "title": "Google Developers",
        "description": "...",
        "customUrl": "@googledevelopers",
        "publishedAt": "2009-05-11T20:36:33Z",
        "thumbnails": {
          "default": {"url": "...", "width": 88, "height": 88},
          "medium": {"url": "...", "width": 240, "height": 240},
          "high": {"url": "...", "width": 800, "height": 800}
        },
        "localized": {"title": "Google Developers", "description": "..."},
        "country": "US"
      },
      "statistics": {
        "viewCount": "1234567890",
        "subscriberCount": "5000000",
        "hiddenSubscriberCount": false,
        "videoCount": "1234"
      }
    }
  ]
}
```

---

## Videos

### List Videos

```
GET /videos
```

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| part | string (required) | `snippet`, `contentDetails`, `statistics`, `status`, `player` |
| id | string | Comma-separated video IDs |
| chart | string | `mostPopular` |
| maxResults | integer | 0-50 (default 5) |

### Get a Video

```bash
curl "https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics&id=VIDEO_ID&key=$API_KEY"
```

### Search Videos

```
GET /search
```

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| part | string (required) | `snippet` |
| q | string | Search query |
| channelId | string | Filter by channel |
| maxResults | integer | 0-50 (default 5) |
| order | string | `date`, `rating`, `relevance`, `title`, `viewCount` |
| type | string | `video`, `channel`, `playlist` |
| videoDuration | string | `short` (<4min), `medium` (4-20min), `long` (>20min) |
| publishedAfter | string | ISO 8601 date |
| publishedBefore | string | ISO 8601 date |

#### Example

```bash
curl "https://www.googleapis.com/youtube/v3/search?part=snippet&q=tutorial&maxResults=10&key=$API_KEY"
```

### Insert Video (Upload)

```
POST /videos
```

Uses resumable upload protocol:

```
POST https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status
```

#### Request Body

```json
{
  "snippet": {
    "title": "My Video Title",
    "description": "Video description",
    "tags": ["tutorial", "programming"],
    "categoryId": "28"
  },
  "status": {
    "privacyStatus": "public",
    "selfDeclaredMadeForKids": false
  }
}
```

### Update Video

```
PUT /videos
```

### Delete Video

```
DELETE /videos?id=VIDEO_ID
```

---

## Playlists

### List Playlists

```
GET /playlists
```

### Create Playlist

```
POST /playlists
```

### Update Playlist

```
PUT /playlists
```

### Delete Playlist

```
DELETE /playlists?id=PLAYLIST_ID
```

---

## Playlist Items

### List Playlist Items

```
GET /playlistItems
```

### Insert Playlist Item

```
POST /playlistItems
```

---

## Comments

### List Comments

```
GET /commentThreads
```

### Insert Comment

```
POST /comments
```

---

## Subscriptions

### List Subscriptions

```
GET /subscriptions
```

### Insert Subscription

```
POST /subscriptions
```

---

## Common Resource Parts

### Video Resource Parts

| Part | Description |
|------|-------------|
| `snippet` | Title, description, tags, thumbnails |
| `contentDetails` | Duration, dimension, definition, caption |
| `statistics` | View count, like count, comment count |
| `status` | Privacy status, upload status |
| `player` | Embedded player HTML |
| `topicDetails` | Topic categories |

### Channel Resource Parts

| Part | Description |
|------|-------------|
| `snippet` | Title, description, thumbnails |
| `contentDetails` | Related playlists |
| `statistics` | View/subscriber/video counts |
| `status` | Privacy status |
| `brandingSettings` | Banner, watermark |

---

## Video Categories

```
GET /videoCategories
```

Common categories:
- 1: Film & Animation
- 2: Autos & Vehicles
- 10: Music
- 17: Sports
- 20: Gaming
- 22: People & Blogs
- 23: Comedy
- 24: Entertainment
- 25: News & Politics
- 26: Howto & Style
- 27: Education
- 28: Science & Technology

---

## Error Response

```json
{
  "error": {
    "code": 403,
    "message": "The request cannot be completed because you have exceeded your quota.",
    "errors": [
      {
        "message": "quotaExceeded",
        "domain": "youtube.quota",
        "reason": "quotaExceeded"
      }
    ],
    "status": "QUOTA_EXCEEDED"
  }
}
```

### Common Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad request / invalid parameters |
| 401 | Authentication required |
| 403 | Quota exceeded or insufficient permissions |
| 404 | Resource not found |

---

## Performance Optimization

### ETags

Use ETags for caching and conditional retrieval:

```
If-None-Match: "ETag-value"
```

Returns 304 Not Modified if unchanged.

### Gzip Compression

Enable gzip by setting:
```
Accept-Encoding: gzip
User-Agent: my-program (gzip)
```

---

## Pagination

Use `nextPageToken` and `prevPageToken` for pagination:

```json
{
  "pageInfo": {
    "totalResults": 100,
    "resultsPerPage": 5
  },
  "nextPageToken": "CDIQAA"
}
```

Include `pageToken=CDIQAA` in next request.
