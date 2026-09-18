# TikTok — Platform Setup Guide

> **Time:** ~30 min active + 1-7 days wait for app review
> **What you need:** TikTok account (Business or Creator), business email

---

## Step 1: Create a TikTok Developer Account

1. Go to **https://developers.tiktok.com**
2. Click **Sign up**
3. Log in with your TikTok account (or create one)
4. Create or join an **Organization**
5. Verify your email

---

## Step 2: Create an App

1. Go to **https://developers.tiktok.com/apps**
2. Click **Connect an app**
3. Select app owner (organization or individual account)
4. Fill in:
   - **App name:** `{STARTUP_NAME}`
   - **Description:** Brief description of what the app does
5. Click **Confirm**

---

## Step 3: Add Products

1. In your app dashboard, click **Add products**
2. Add these products:

| Product | What It Does |
|---------|-------------|
| **Login Kit** | OAuth authentication |
| **Content Posting API** | Post videos/photos directly |

> **Note:** You need the Content Posting API for scheduling posts. This requires review.

---

## Step 4: Configure OAuth

1. Go to **Login Kit** → **Settings**
2. Set **Redirect URI:**
   ```
   https://your-postiz-domain.com/integrations/social/tiktok
   ```
   (or for local dev: `http://localhost:5000/integrations/social/tiktok`)
3. Save

---

## Step 5: Configure Content Posting API

1. Go to **Content Posting API** → **Settings**
2. Set **Content Posting API upload URL:**
   ```
   https://your-postiz-domain.com
   ```
3. Verify the URL (download the verification file, upload it to your domain root)
4. Save

---

## Step 6: Set Up URL Verification

For apps created after September 9, 2024, you must verify:

1. **Terms of Service URL** → Add your TOS page
2. **Privacy Policy URL** → Add your privacy policy page
3. **Web/Desktop URL** → Add your website URL

**Verification methods:**
- **By Domain:** Enter your domain and subdomain
- **By URL prefix:** Enter full URL, download signature file, upload to URL

---

## Step 7: Request Permissions

1. Go to **App Review** → **Permissions and Features**
2. Request these scopes:

| Scope | What It Does |
|-------|-------------|
| `user.info.basic` | Read basic user info |
| `video.publish` | Publish videos |
| `video.list` | List user videos |

---

## Step 8: Submit for Review

1. Go to **App Review** → **Submit for Review**
2. For each product/scope:
   - Explain how you use it
   - Upload a demo video (max 5 videos, 50MB each) showing the end-to-end flow
3. Save and submit

> **Review takes 1-7 days.** TikTok reviews each scope individually.

---

## Step 9: Copy Credentials to Postiz/SteveJobless

From your app dashboard → **Basic Info**, copy:

```
TIKTOK_CLIENT_KEY=your_client_key
TIKTOK_CLIENT_SECRET=your_client_secret
```

Set these in your Postiz `.env` file.

---

## Step 10: Connect the Channel in Postiz

1. Open Postiz → **Add Channel**
2. Select **TikTok**
3. Authorize the app in the OAuth popup
4. Done

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| "Redirect URI mismatch" | Ensure URI in TikTok dashboard matches Postiz exactly |
| "Content Posting API not available" | Submit app for review first |
| Posts fail with permission error | Scope not approved → check App Review status |
| "App not in production" | Switch from Sandbox to Production mode |

---

## Checklist

- [ ] Developer account created with organization
- [ ] App created
- [ ] Login Kit added and configured
- [ ] Content Posting API added and configured
- [ ] Redirect URI set
- [ ] URL verification completed
- [ ] All permissions requested with demo videos
- [ ] App submitted for review
- [ ] App approved (wait 1-7 days)
- [ ] Credentials copied to Postiz
- [ ] Channel connected in Postiz
