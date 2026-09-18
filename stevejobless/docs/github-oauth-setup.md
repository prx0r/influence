# GitHub OAuth Apps Setup Guide

**Docs:** https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/creating-an-oauth-app

## Create an OAuth App

1. Go to GitHub → Profile picture → **Settings**
2. Click **Developer settings** in left sidebar
3. Click **OAuth apps**
4. Click **New OAuth App**
5. Fill in:
   - **Application name**: Your app name (public)
   - **Homepage URL**: Full URL to your app's website
   - **Application description**: Optional description
   - **Authorization callback URL**: Your app's callback URL
6. (Optional) Enable Device Flow
7. Click **Register application**

## Generate Client Secret

After registration, click **Generate a new client secret**.

## OAuth Flow

```
https://github.com/login/oauth/authorize
  ?client_id=YOUR_CLIENT_ID
  &scope=repo,user
  &redirect_uri=YOUR_CALLBACK_URL
```

Exchange code for token:
```bash
POST https://github.com/login/oauth/access_token
{
  "client_id": "YOUR_CLIENT_ID",
  "client_secret": "YOUR_CLIENT_SECRET",
  "code": "AUTHORIZATION_CODE"
}
```

## Scopes

| Scope | Access |
|-------|--------|
| `repo` | Full repository access |
| `user` | Profile and email |
| `read:org` | Organization membership |
| `admin:repo_hook` | Webhook management |

## Environment Variables

```bash
GITHUB_CLIENT_ID=your_client_id
GITHUB_CLIENT_SECRET=your_client_secret
```

## GitHub Apps vs OAuth Apps

Consider GitHub Apps instead:
- Fine-grained permissions
- Short-lived tokens
- Can act independently of users
- Better for production use
