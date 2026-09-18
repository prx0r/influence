# X (Twitter) API v2 Documentation

Base URL: `https://api.x.com/2`

Authentication: `Authorization: Bearer <BEARER_TOKEN>` (OAuth 2.0 App-Only for public data) or OAuth 2.0 User Context for user-specific actions.

## Key Concepts

### Fields and Expansions

The X API v2 returns minimal data by default. Use `fields` parameters to request additional data.

| Object | Parameter | Documentation |
|--------|-----------|---------------|
| Post (Tweet) | `tweet.fields` | Tweet fields |
| User | `user.fields` | User fields |
| Media | `media.fields` | Media fields |
| Poll | `poll.fields` | Poll fields |
| Place | `place.fields` | Place fields |

### Default Tweet Fields
- `id`
- `text`
- `edit_history_tweet_ids`

### Common Field Combinations

**User profiles:**
```
user.fields=created_at,description,location,public_metrics,verified
```

**Full post context:**
```
tweet.fields=created_at,author_id,conversation_id,in_reply_to_user_id,referenced_tweets
expansions=author_id,referenced_tweets.id
user.fields=username,name
```

---

## Posts (Tweets)

### Create a Tweet

```
POST /tweets
```

#### Body Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| text | string (required) | Tweet text (max 280 chars) |
| reply.in_reply_to_tweet_id | string | ID of tweet to reply to |
| media.media_ids | array | Array of media IDs to attach |
| poll.options | array | Poll options (2-4 items) |
| poll.duration_minutes | integer | Poll duration (5-10080 minutes) |
| quote_tweet_id | string | ID of tweet to quote |
| reply.exclude_reply_user_ids | array | User IDs to exclude from reply |

#### Example

```bash
curl -X POST "https://api.x.com/2/tweets" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello from the X API v2! #TwitterDev"
  }'
```

### Get a Tweet

```
GET /tweets/{id}
```

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| tweet.fields | string | Comma-separated field names |
| expansions | string | Related objects to include |
| media.fields | string | Fields for media objects |
| user.fields | string | Fields for user objects |

#### Example

```bash
curl "https://api.x.com/2/tweets/1234567890?tweet.fields=created_at,public_metrics,author_id" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

### Delete a Tweet

```
DELETE /tweets/{id}
```

```bash
curl -X DELETE "https://api.x.com/2/tweets/1234567890" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

### Search Tweets

```
GET /tweets/search/recent
```

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| query | string (required) | Search query |
| start_time | string | ISO 8601 start time |
| end_time | string | ISO 8601 end time |
| max_results | integer | 10-100 (default 10) |
| tweet.fields | string | Additional fields |
| expansions | string | Related objects |
| next_token | string | Pagination token |

#### Example

```bash
curl "https://api.x.com/2/tweets/search/recent?query=X%20API&max_results=10" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

### Get User's Tweets

```
GET /users/{id}/tweets
```

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| max_results | integer | 5-100 (default 10) |
| pagination_token | string | Pagination token |
| start_time | string | ISO 8601 start time |
| end_time | string | ISO 8601 end time |
| tweet.fields | string | Additional fields |

### Retweet a Tweet

```
POST /users/{id}/retweets
```

```bash
curl -X POST "https://api.x.com/2/users/123456/retweets" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tweet_id": "1234567890"}'
```

### Unretweet a Tweet

```
DELETE /users/{id}/retweets/{source_tweet_id}
```

### Like a Tweet

```
POST /users/{id}/likes
```

```bash
curl -X POST "https://api.x.com/2/users/123456/likes" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tweet_id": "1234567890"}'
```

### Unlike a Tweet

```
DELETE /users/{id}/likes/{tweet_id}
```

---

## Users

### Get a User

```
GET /users/{id}
```

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| user.fields | string | Additional fields |

### Get User by Username

```
GET /users/by/username/{username}
```

#### Example

```bash
curl "https://api.x.com/2/users/by/username/xdevelopers?user.fields=created_at,description,public_metrics" \
  -H "Authorization: Bearer $BEARER_TOKEN"
```

#### Response

```json
{
  "data": {
    "id": "2244994945",
    "name": "Twitter Dev",
    "username": "xdevelopers",
    "created_at": "2013-12-14T04:35:55.000Z",
    "description": "The voice of the X Developer Platform",
    "public_metrics": {
      "followers_count": 570842,
      "following_count": 2048,
      "tweet_count": 14052,
      "listed_count": 1672
    }
  }
}
```

### Get Multiple Users

```
GET /users?ids=123456,789012
```

### Get Users by Usernames

```
GET /users/by?usernames=alice,bob
```

### Get User's Followers

```
GET /users/{id}/followers
```

### Get User's Following

```
GET /users/{id}/following
```

---

## User Fields Reference

| Field | Type | Description |
|-------|------|-------------|
| id | string | User ID |
| name | string | Display name |
| username | string | Handle (without @) |
| description | string | Bio |
| created_at | string | Account creation date |
| public_metrics | object | followers_count, following_count, tweet_count, listed_count |
| profile_image_url | string | Profile image URL |
| location | string | User location |
| url | string | Website URL |
| verified | boolean | Verified status |
| protected | boolean | Protected account |

---

## Tweet Fields Reference

| Field | Type | Description |
|-------|------|-------------|
| id | string | Tweet ID |
| text | string | Tweet text |
| created_at | string | Creation timestamp |
| author_id | string | Author user ID |
| conversation_id | string | Conversation thread ID |
| in_reply_to_user_id | string | Reply target user ID |
| referenced_tweets | array | Quote/retweet references |
| public_metrics | object | retweet_count, reply_count, like_count, quote_count, bookmark_count, impression_count |
| entities | object | URLs, hashtags, mentions |
| attachments | object | Media keys |
| lang | string | Language |
| source | string | Client used to post |

---

## Timeline

### User Tweet Timeline

```
GET /users/{id}/tweets
```

### Home Timeline (Requires OAuth 2.0 User Context)

```
GET /users/{id}/timelines/reverse_chronological
```

---

## Lists

### Get User's Lists

```
GET /users/{id}/owned_lists
```

### Get List Tweets

```
GET /lists/{id}/tweets
```

---

## Spaces

### Search Spaces

```
GET /spaces/search
```

### Get a Space

```
GET /spaces/{id}
```

---

## Compliance

### Batch Compliance

```
POST /compliance/jobs
```

```bash
curl -X POST "https://api.x.com/2/compliance/jobs" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"type": "tweets", "name": "my-compliance-job"}'
```

---

## Rate Limits

### Tweet Creation (POST /tweets)
- **App-only (Bearer):** 200 requests per 15 minutes per app
- **User context (OAuth 2.0):** 200 requests per 15 minutes per user

### Tweet Lookup (GET /tweets)
- **App-only:** 900 requests per 15 minutes per app
- **User context:** 900 requests per 15 minutes per user

### Search (GET /tweets/search/recent)
- **App-only:** 450 requests per 15 minutes per app

### User Lookup (GET /users)
- **App-only:** 900 requests per 15 minutes per app

### Rate Limit Headers

```
x-rate-limit-limit: 900
x-rate-limit-remaining: 899
x-rate-limit-reset: 1697000000
```

---

## Error Format

```json
{
  "errors": [
    {
      "message": "Invalid Request: One or more parameters to your request was invalid.",
      "code": 215
    }
  ]
}
```

### Common Error Codes

| Code | Description |
|------|-------------|
| 215 | Invalid request parameters |
| 32 | Could not authenticate |
| 63 | Suspended account |
| 88 | Rate limit exceeded |
| 130 | Over capacity |
| 131 | Internal error |

---

## Pagination

Use `pagination_token` from response to get next page:

```json
{
  "meta": {
    "result_count": 10,
    "next_token": "DAABCgACGdyWgAA..."
  }
}
```

Include `next_token` in next request to get next page.
