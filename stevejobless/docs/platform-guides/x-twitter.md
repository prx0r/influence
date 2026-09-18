# X (Twitter) — Platform Setup Guide

> **Time:** ~20 min active (no approval wait for basic posting)
> **What you need:** X account, business email, $7 for API credits (required for posting)

---

## Step 1: Create a Developer Account

1. Go to **https://developer.x.com/en/portal/dashboard**
2. Log in with your X account
3. Apply for a developer account
4. Fill in:
   - **Use case:** "Making a social media management tool for my own business"
   - **Description:** Describe what you'll use the API for
5. Accept the terms
6. Verify your email

---

## Step 2: Create a Project and App

1. In the Developer Portal, click **Create Project**
2. Fill in:
   - **Project name:** `{STARTUP_NAME}`
   - **Use case:** "Making a tool or service"
   - **Description:** Brief description
3. Click **Create App**
4. Name your app (e.g., `{STARTUP_NAME}-app`)

---

## Step 3: Set App Permissions

> **IMPORTANT:** Do this BEFORE generating tokens. Default is Read-only.

1. Go to **App Settings** → **User authentication settings**
2. Click **Edit** under **App permissions**
3. Select **Read and Write**
4. Under **Type of App**, select **Automated App or Bot**
5. Fill in:
   - **Callback URI:** `https://your-postiz-domain.com/integrations/social/x`
     (or for local dev: `http://localhost:5000/integrations/social/x`)
   - **Website URL:** `https://your-domain.com`
6. Click **Save**

---

## Step 4: Generate Keys and Tokens

1. Go to **Keys and Tokens**
2. Click **Regenerate** next to:
   - **API Key** (Consumer Key)
   - **API Key Secret** (Consumer Secret)
   - **Access Token and Secret**
   - **Bearer Token**
3. Copy all four values immediately (they won't be shown again)

---

## Step 5: Add API Credits (Required for Posting)

> **X's free tier is READ-ONLY.** You MUST add credits to post tweets.

1. Go to **Projects** → **App** → **Usage Tiers**
2. Click **Add payment method**
3. Add a credit card
4. Purchase the **Basic** tier ($7/month minimum)
5. Write endpoints unlock immediately after payment

**What you get with Basic:**
- 10,000 tweets per month (post, delete, like)
- 50,000 tweets per month (read)
- Search, user lookup, etc.

---

## Step 6: Copy Credentials to Postiz/SteveJobless

From **Keys and Tokens**, copy:

```
X_API_KEY=your_api_key
X_API_SECRET=your_api_key_secret
X_ACCESS_TOKEN=your_access_token
X_ACCESS_TOKEN_SECRET=your_access_token_secret
```

Set these in your Postiz `.env` file.

---

## Step 7: Connect the Channel in Postiz

1. Open Postiz → **Add Channel**
2. Select **X (Twitter)**
3. Authorize the app in the OAuth popup
4. Done

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| "Unauthorized" | Tokens not generated with Read+Write permissions → regenerate |
| "402 Payment Required" | Add credits in Developer Portal billing |
| Posts work but media doesn't | Free tier doesn't support media → upgrade to Basic |
| "Invalid token" | Regenerate Access Token and Secret |

---

## Checklist

- [ ] Developer account created and approved
- [ ] Project and App created
- [ ] App permissions set to Read+Write BEFORE generating tokens
- [ ] App type set to Automated App or Bot
- [ ] Callback URI and Website URL configured
- [ ] All four keys/tokens generated and copied
- [ ] API credits added ($7/month minimum)
- [ ] Credentials set in Postiz `.env`
- [ ] Channel connected in Postiz
