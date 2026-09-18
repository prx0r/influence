# X/Twitter API v2 Setup

**Docs:** https://developer.x.com/en/docs/twitter-api
**Portal:** https://developer.x.com/en/portal/dashboard
**Samples:** https://github.com/xdevplatform/samples

## Quick Start

### 1. Get API Credentials

Sign up at [X Developer Portal](https://developer.x.com/en/portal/dashboard).

### 2. Authentication Types

| Type | Use Case | Env Vars |
|------|----------|----------|
| Bearer Token | Read-only (search, lookup) | `BEARER_TOKEN` |
| OAuth 2.0 PKCE | User actions (post, like, repost) | `CLIENT_ID`, `CLIENT_SECRET` |
| OAuth 1.0a | Legacy endpoints | `CONSUMER_KEY`, `CONSUMER_SECRET` |

### 3. Set Environment Variables

```bash
export BEARER_TOKEN='your_bearer_token'
export CLIENT_ID='your_client_id'
export CLIENT_SECRET='your_client_secret'
```

## App Permissions

**Important:** Default permission is Read-only. Change BEFORE generating tokens.

1. Go to **App Settings** → **User authentication settings**
2. Set:
   - **App permissions**: Read and Write
   - **Type of App**: Automated App or Bot
   - **Callback URI**: `https://yourdomain.com/`
   - **Website URL**: `https://yourdomain.com`
3. Save, then go to **Keys and Tokens** → **Regenerate** Access Token and Secret

## The 402 Wall

X API free tier is read-only. To write (post tweets):
- Go to developer portal billing section
- Add credits ($7 minimum to start)
- Write endpoints unlock immediately

## Posting Tweets (Node.js)

```bash
npm install twitter-api-v2
```

```javascript
const { TwitterApi } = require('twitter-api-v2');

const client = new TwitterApi({
  appKey: process.env.X_API_KEY,
  appSecret: process.env.X_API_SECRET,
  accessToken: process.env.X_ACCESS_TOKEN,
  accessSecret: process.env.X_ACCESS_TOKEN_SECRET,
});

const tweet = await client.v2.tweet("Hello from the API!");
console.log('Posted:', tweet.data.id);
```

## Environment Variables

```bash
X_API_KEY=your_consumer_key
X_API_SECRET=your_consumer_secret
X_ACCESS_TOKEN=your_access_token
X_ACCESS_TOKEN_SECRET=your_access_token_secret
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/2/tweets` | POST | Create tweet |
| `/2/tweets/:id` | GET | Get tweet |
| `/2/tweets/search/recent` | GET | Search recent tweets |
| `/2/users/:id/following` | POST | Follow user |
| `/2/users/:id/likes` | POST | Like tweet |

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| Tweet creation | 200/15min (app), 50/15min (user) |
| Search | 450/15min |
| User lookup | 900/15min |
