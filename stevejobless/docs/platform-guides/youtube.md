# YouTube (Google) — Platform Setup Guide

> **Time:** ~25 min active (no approval wait for basic access)
> **What you need:** Google account, business email

---

## Step 1: Create a Google Cloud Project

1. Go to **https://console.cloud.google.com**
2. Log in with your Google account
3. Click **Select a Project** → **New Project**
4. Fill in:
   - **Project name:** `{STARTUP_NAME}`
   - **Organization:** Select your org (or "No organization")
5. Click **Create**
6. Select the new project

---

## Step 2: Enable YouTube Data API v3

1. In Google Cloud Console, go to **APIs & Services** → **Library**
2. Search for **YouTube Data API v3**
3. Click on it → click **Enable**

---

## Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Select **External** (unless you have a Google Workspace org)
3. Fill in:
   - **App name:** `{STARTUP_NAME}`
   - **User support email:** your email
   - **Developer contact email:** your email
4. Click **Save and Continue**
5. **Scopes:** Click **Add or Remove Scopes** → add:
   - `https://www.googleapis.com/auth/youtube`
   - `https://www.googleapis.com/auth/youtube.upload`
   - `https://www.googleapis.com/auth/youtube.readonly`
6. Click **Save and Continue**
7. **Test users:** Add the Google accounts that will use this app
8. Click **Save and Continue**

---

## Step 4: Create OAuth Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID**
3. Application type: **Web application**
4. Name: `{STARTUP_NAME}-oauth`
5. **Authorized redirect URIs:** add:
   ```
   https://your-postiz-domain.com/integrations/social/youtube
   ```
   (or for local dev: `http://localhost:5000/integrations/social/youtube`)
6. Click **Create**
7. Copy the **Client ID** and **Client Secret**

---

## Step 5: Publish Your OAuth App

> **Important:** Apps in "Testing" mode expire tokens after 7 days. Publish to production for persistent tokens.

1. Go to **OAuth consent screen**
2. Click **Publish App**
3. Confirm

> **Note:** If your app requests sensitive scopes (like `youtube.upload`), Google may require verification. For personal/business use with a small number of users, this is usually not required.

---

## Step 6: Copy Credentials to Postiz/SteveJobless

From the OAuth credentials page, copy:

```
YOUTUBE_CLIENT_ID=your_client_id
YOUTUBE_CLIENT_SECRET=your_client_secret
```

Set these in your Postiz `.env` file.

---

## Step 7: Connect the Channel in Postiz

1. Open Postiz → **Add Channel**
2. Select **YouTube**
3. Authorize the app in the Google OAuth popup
4. Select which YouTube channel to connect (if you have multiple)
5. Done

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| Tokens expire after 7 days | Publish your OAuth app to production |
| "Access blocked" | App in Testing mode → publish it |
| "Quota exceeded" | YouTube API has 10,000 units/day default → request increase in Cloud Console |
| "Redirect URI mismatch" | Ensure URI in Google Cloud Console matches Postiz exactly |

---

## API Quotas

| Operation | Units per request |
|-----------|-------------------|
| Search | 100 |
| Videos list | 1 |
| Channels list | 1 |
| Upload | 1,600 |

Default: 10,000 units/day. Request increase via Cloud Console if needed.

---

## Checklist

- [ ] Google Cloud project created
- [ ] YouTube Data API v3 enabled
- [ ] OAuth consent screen configured with correct scopes
- [ ] OAuth credentials created with redirect URI
- [ ] App published to production
- [ ] Client ID and Secret copied to Postiz `.env`
- [ ] Channel connected in Postiz
