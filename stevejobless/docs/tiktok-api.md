# TikTok Developer API Documentation

Base URL: `https://open.tiktokapis.com/v2`

Authentication: `Authorization: Bearer <USER_ACCESS_TOKEN>`

## Content Posting API

The Content Posting API allows you to post content (videos and photos) directly to TikTok.

### Prerequisites

1. A registered app on TikTok for Developers
2. Content Posting API product added to your app
3. Direct Post configuration enabled
4. `video.publish` scope approved and authorized
5. Access token and open ID of the authorized user

---

## Direct Post Endpoints

### Query Creator Info

Returns information about the creator's account needed for posting.

```
POST /v2/post/publish/creator_info/query/
```

#### Request

```bash
curl --location --request POST 'https://open.tiktokapis.com/v2/post/publish/creator_info/query/' \
--header 'Authorization: Bearer <ACCESS_TOKEN>' \
--header 'Content-Type: application/json; charset=UTF-8'
```

#### Response

```json
{
  "data": {
    "creator_avatar_url": "https://...",
    "creator_username": "tiktok",
    "creator_nickname": "TikTok Official",
    "privacy_level_options": ["PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS", "SELF_ONLY"],
    "comment_disabled": false,
    "duet_disabled": false,
    "stitch_disabled": true,
    "max_video_post_duration_sec": 300
  },
  "error": {
    "code": "ok",
    "message": ""
  }
}
```

---

### Post a Video (Direct Post)

Initialize video upload on TikTok's server.

```
POST /v2/post/publish/video/init/
```

#### Body Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| post_info | object | yes | Post metadata |
| post_info.title | string | yes | Video caption (max 2200 UTF-16 runes) |
| post_info.privacy_level | string | yes | `PUBLIC_TO_EVERYONE`, `MUTUAL_FOLLOW_FRIENDS`, `FOLLOWER_OF_CREATOR`, `SELF_ONLY` |
| post_info.disable_duet | boolean | no | Disable duets |
| post_info.disable_stitch | boolean | no | Disable stitches |
| post_info.disable_comment | boolean | no | Disable comments |
| post_info.video_cover_timestamp_ms | int32 | no | Cover frame timestamp |
| post_info.brand_content_toggle | boolean | yes | Paid partnership |
| post_info.brand_organic_toggle | boolean | yes | Creator's own business |
| post_info.is_aigc | boolean | no | AI-generated content |
| source_info | object | yes | Upload source |
| source_info.source | string | yes | `FILE_UPLOAD` or `PULL_FROM_URL` |
| source_info.video_url | string | yes* | Video URL (for PULL_FROM_URL) |
| source_info.video_size | int64 | yes* | Video file size in bytes (for FILE_UPLOAD) |
| source_info.chunk_size | int64 | no | Chunk size in bytes |
| source_info.total_chunk_count | int64 | no | Total number of chunks |

#### Example - FILE_UPLOAD

```bash
curl --location 'https://open.tiktokapis.com/v2/post/publish/video/init/' \
--header 'Authorization: Bearer <ACCESS_TOKEN>' \
--header 'Content-Type: application/json; charset=UTF-8' \
--data-raw '{
  "post_info": {
    "title": "Funny cat video #cat #fyp",
    "privacy_level": "PUBLIC_TO_EVERYONE",
    "disable_duet": false,
    "disable_comment": true,
    "disable_stitch": false,
    "brand_content_toggle": false,
    "brand_organic_toggle": false
  },
  "source_info": {
    "source": "FILE_UPLOAD",
    "video_size": 50000123,
    "chunk_size": 10000000,
    "total_chunk_count": 5
  }
}'
```

#### Response

```json
{
  "data": {
    "publish_id": "v_pub_file~v2-1.123456789",
    "upload_url": "https://open-upload.tiktokapis.com/video/?upload_id=67890&upload_token=Xza123"
  },
  "error": {
    "code": "ok",
    "message": ""
  }
}
```

#### Example - PULL_FROM_URL

```bash
curl --location 'https://open.tiktokapis.com/v2/post/publish/video/init/' \
--header 'Authorization: Bearer <ACCESS_TOKEN>' \
--header 'Content-Type: application/json; charset=UTF-8' \
--data-raw '{
  "post_info": {
    "title": "Funny cat video #cat #fyp",
    "privacy_level": "PUBLIC_TO_EVERYONE",
    "disable_duet": false,
    "disable_comment": true,
    "disable_stitch": false,
    "brand_content_toggle": false,
    "brand_organic_toggle": false
  },
  "source_info": {
    "source": "PULL_FROM_URL",
    "video_url": "https://example.verified.domain.com/video.mp4"
  }
}'
```

---

### Upload Video to TikTok Servers

After initializing with FILE_UPLOAD, send the video to the returned upload_url:

```bash
curl --location --request PUT 'https://open-upload.tiktokapis.com/upload/?upload_id=67890&upload_token=Xza123' \
--header 'Content-Range: bytes 0-30567099/30567100' \
--header 'Content-Type: video/mp4' \
--data '@/path/to/file/video.mp4'
```

The upload_url is valid for **one hour** after issuance.

---

### Post Photos (Direct Post)

```
POST /v2/post/publish/content/init/
```

#### Body Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| post_info | object | yes | Post metadata |
| post_info.title | string | no | Photo caption |
| post_info.description | string | no | Description |
| post_info.disable_comment | boolean | no | Disable comments |
| post_info.privacy_level | string | yes | Privacy level |
| post_info.auto_add_music | boolean | yes | Auto-add music |
| source_info | object | yes | Upload source |
| source_info.source | string | yes | `PULL_FROM_URL` |
| source_info.photo_cover_index | int | yes | Cover image index |
| source_info.photo_images | array | yes | Array of image URLs |
| post_mode | string | yes | `DIRECT_POST` or `MEDIA_UPLOAD` |
| media_type | string | yes | `PHOTO` |

#### Example

```bash
curl --location 'https://open.tiktokapis.com/v2/post/publish/content/init/' \
--header 'Authorization: Bearer <ACCESS_TOKEN>' \
--header 'Content-Type: application/json' \
--data-raw '{
    "post_info": {
        "title": "Beautiful sunset #photography",
        "description": "Amazing sunset photo",
        "disable_comment": false,
        "privacy_level": "PUBLIC_TO_EVERYONE",
        "auto_add_music": true
    },
    "source_info": {
        "source": "PULL_FROM_URL",
        "photo_cover_index": 1,
        "photo_images": [
            "https://example.com/image1.jpg",
            "https://example.com/image2.jpg"
        ]
    },
    "post_mode": "DIRECT_POST",
    "media_type": "PHOTO"
}'
```

---

### Get Post Status

Check the status of a post using the publish_id.

```
POST /v2/post/publish/status/fetch/
```

#### Request

```bash
curl --location 'https://open.tiktokapis.com/v2/post/publish/status/fetch/' \
--header 'Authorization: Bearer <ACCESS_TOKEN>' \
--header 'Content-Type: application/json; charset=UTF-8' \
--data '{
    "publish_id": "v_pub_url~v2.123456789"
}'
```

---

## Upload to TikTok (Draft)

Instead of DIRECT_POST, use MEDIA_UPLOAD to send content as a draft.

### Video Upload to Draft

```
POST /v2/post/publish/inbox/video/init/
```

### Photo Upload to Draft

```
POST /v2/post/publish/content/init/
```

Set `post_mode` to `MEDIA_UPLOAD` instead of `DIRECT_POST`.

---

## Authentication

### User Access Token

Obtained through OAuth 2.0 flow:

1. Redirect user to TikTok authorization
2. Exchange code for access token
3. Use token in Authorization header

```
Authorization: Bearer <USER_ACCESS_TOKEN>
```

### Required Scopes

| Scope | Description |
|-------|-------------|
| `video.publish` | Post videos and photos directly |
| `video.upload` | Upload drafts to TikTok |

---

## Error Codes

| HTTP Status | Error Code | Description |
|-------------|------------|-------------|
| 400 | `invalid_param` | Check error message |
| 403 | `spam_risk_too_many_posts` | Daily post cap reached |
| 403 | `spam_risk_user_banned_from_posting` | User banned from posting |
| 403 | `reached_active_user_cap` | Daily active user quota reached |
| 403 | `unaudited_client_can_only_post_to_private_accounts` | Unaudited client restriction |
| 403 | `url_ownership_unverified` | URL prefix not verified |
| 403 | `privacy_level_option_mismatch` | Invalid privacy level |
| 401 | `access_token_invalid` | Token invalid or expired |
| 401 | `scope_not_authorized` | Missing video.publish scope |
| 429 | `rate_limit_exceeded` | Rate limit exceeded |
| 5xx | - | Server error, retry later |

---

## Video Restrictions

| Parameter | Requirement |
|-----------|-------------|
| Format | MP4 + H.264 (recommended) |
| Duration | 3-180 seconds (up to 300 for some creators) |
| File Size | Up to 500MB |
| Resolution | 720p+ recommended |
| Frame Rate | 30fps or 60fps |

## Photo Restrictions

| Parameter | Requirement |
|-----------|-------------|
| Format | JPG, PNG, WEBP |
| File Size | Up to 20MB per image |
| Max Photos | Up to 35 per post |
| Resolution | 1080x1920 recommended |

---

## Important Notes

1. **Unaudited clients**: Content posted by unaudited clients is restricted to private viewing
2. **Audit required**: To lift visibility restrictions, your API client must undergo an audit
3. **Upload URL expiry**: FILE_UPLOAD URLs expire after 1 hour
4. **Daily limits**: There are daily posting caps per user and per client
