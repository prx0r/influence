# YouTube Data API Setup

**Docs:** https://developers.google.com/youtube/v3
**Console:** https://console.cloud.google.com

## Quick Start

### 1. Create Project and Enable API

1. Open [Google API Console](https://console.cloud.google.com)
2. Create or select a project
3. Go to **Library** → Search "YouTube Data API v3" → Enable

### 2. Create Credentials

#### API Key (for public data)
1. Go to **Credentials** → **Create credentials** → **API key**
2. Restrict key to YouTube Data API only

#### OAuth 2.0 (for user data)
1. Go to **Credentials** → **Create credentials** → **OAuth client ID**
2. Application type: **Web application**
3. Add Authorized JavaScript origins: `http://localhost:8000`
4. Add Authorized redirect URIs (as needed)

### 3. Download Credentials

Download `client_secret.json` from the Console. Store securely.

## Authentication

### API Key (Public Data)
```bash
curl "https://www.googleapis.com/youtube/v3/channels?part=snippet&id=CHANNEL_ID&key=YOUR_API_KEY"
```

### OAuth 2.0 (User Data)

**Authorization URL:**
```
https://accounts.google.com/o/oauth2/v2/auth
  ?client_id=YOUR_CLIENT_ID
  &redirect_uri=YOUR_REDIRECT_URI
  &response_type=code
  &scope=https://www.googleapis.com/auth/youtube.readonly
  &access_type=offline
  &state=RANDOM_STATE_STRING
```

**Exchange Code for Token:**
```bash
POST https://oauth2.googleapis.com/token
{
  "client_id": "YOUR_CLIENT_ID",
  "client_secret": "YOUR_CLIENT_SECRET",
  "code": "AUTHORIZATION_CODE",
  "grant_type": "authorization_code",
  "redirect_uri": "YOUR_REDIRECT_URI"
}
```

## Scopes

| Scope | Access |
|-------|--------|
| `youtube.readonly` | Read-only access |
| `youtube` | Full YouTube access |
| `youtube.upload` | Upload videos |
| `youtube.force-ssl` | Force HTTPS |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/youtube/v3/channels` | GET | List channels |
| `/youtube/v3/videos` | GET | List videos |
| `/youtube/v3/search` | GET | Search videos |
| `/youtube/v3/playlists` | GET | List playlists |
| `/youtube/v3/captions` | GET/POST | Manage captions |

## Example: List Channel Videos

```bash
curl "https://www.googleapis.com/youtube/v3/search?part=snippet&channelId=CHANNEL_ID&maxResults=10&key=API_KEY"
```

## Python Client Library

```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

```python
from googleapiclient.discovery import build

youtube = build('youtube', 'v3', developerKey='YOUR_API_KEY')
request = youtube.search().list(
    part='snippet',
    q='python tutorial',
    maxResults=10
)
response = request.execute()
```

## Rate Limits

- 10,000 units per day (default)
- Search: 100 units per request
- Videos list: 1 unit per request
- Quota increase: Request via Google Cloud Console

## Embed in Apps

```javascript
// YouTube IFrame Player API
var player;
function onYouTubeIframeAPIReady() {
  player = new YT.Player('player', {
    height: '360',
    width: '640',
    videoId: 'VIDEO_ID',
  });
}
```
