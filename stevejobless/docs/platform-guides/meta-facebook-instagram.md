# Meta (Facebook + Instagram) — Platform Setup Guide

> **Time:** ~45 min active + 3-14 days wait for business verification
> **What you need:** Business email, business name, domain, business registration doc

---

## Step 1: Create a Meta Developer Account

1. Go to **https://developers.facebook.com**
2. Click **Get Started**
3. Log in with your personal Facebook account (required by Meta)
4. Accept the terms
5. Verify your email

> **Note:** You need a personal Facebook account. Meta requires it. There's no way around this.

---

## Step 2: Create a Facebook App

1. Go to **https://developers.facebook.com/apps/create**
2. Select **Business** → click **Next**
3. Fill in:
   - **App name:** `{STARTUP_NAME}` (e.g., "Feedify")
   - **App contact email:** your business email
   - **Business Portfolio:** Select your business portfolio (or create one)
4. Click **Create App**
5. Complete the security check

---

## Step 3: Add Facebook Login Product

1. In your app dashboard, click **Add Product**
2. Find **Facebook Login** → click **Set Up**
3. Select **Web** platform
4. Enter your **Valid OAuth Redirect URIs:**
   ```
   https://your-postiz-domain.com/integrations/social/facebook
   ```
   (or for local dev: `http://localhost:5000/integrations/social/facebook`)
5. Enter your **Site URL:** `https://your-domain.com`
6. Click **Save**

---

## Step 4: Configure Permissions

1. In your app dashboard, go to **App Settings** → **Basic**
2. Fill in:
   - **App Domains:** `your-domain.com` (without https://)
   - **Privacy Policy URL:** `https://your-domain.com/privacy`
   - **Terms of Service URL:** `https://your-domain.com/terms`
   - **Category:** Select the most relevant one
3. Click **Save Changes**

---

## Step 5: Request Advanced Permissions

1. Go to **App Review** → **Permissions and Features**
2. Find and request access for each of these:

| Permission | What It Does |
|------------|-------------|
| `pages_show_list` | List your Facebook Pages |
| `business_management` | Manage business assets |
| `pages_manage_posts` | Create/delete posts on Pages |
| `pages_manage_engagement` | Manage comments/reactions |
| `pages_read_engagement` | Read engagement data |
| `instagram_basic` | Read Instagram account info |
| `instagram_content_publish` | Publish to Instagram |
| `instagram_manage_comments` | Manage Instagram comments |
| `instagram_manage_insights` | Read Instagram analytics |

3. For each permission, provide:
   - Description of how you use it
   - A screencast showing the flow (screen record yourself connecting the account)

---

## Step 6: Business Verification

1. Go to **Business Settings** → **Security Center**
2. Click **Start Verification**
3. Submit:
   - Business registration document (certificate of incorporation, etc.)
   - Bank statement or utility bill (proof of address)
   - Domain ownership verification (add DNS TXT record or upload HTML file)
4. Wait 3-14 days for Meta to review

> **This is the hard wall.** Meta manually reviews business documents. No way to speed this up.

---

## Step 7: Connect Instagram (if needed)

Instagram requires a **Business** or **Creator** account linked to a Facebook Page.

1. Open Instagram app → **Settings** → **Account** → **Switch to Professional Account**
2. Select **Business** or **Creator**
3. Link to your Facebook Page (create one if needed)
4. Go back to Meta Developer Dashboard → **App Roles** → **Roles**
5. Add the Instagram account as an **Instagram Tester**
6. Have the Instagram account holder accept the tester invitation in **Settings** → **Apps and Websites** → **Tester Invitations**

---

## Step 8: Set App to Live Mode

1. Go to **App Settings** → **Basic**
2. Change **App Mode** from **Development** to **Live**
3. Confirm

> **Important:** In Development mode, posts with media are only visible to app developers/testers. Switch to Live for public visibility.

---

## Step 9: Copy Credentials to Postiz/SteveJobless

From **App Settings** → **Basic**, copy:

```
FACEBOOK_APP_ID=your_app_id
FACEBOOK_APP_SECRET=your_app_secret
```

Set these in your Postiz `.env` file.

---

## Step 10: Connect the Channel in Postiz

1. Open Postiz → **Add Channel**
2. Select **Facebook** or **Instagram (FB-linked)**
3. Authorize the app in the OAuth popup
4. Select which Page/Account to connect
5. Done

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| "Domain of this URL isn't included in the app's domains" | Add domain to App Domains + fill Category + Save |
| "Invalid Scopes: pages_read_user_content" | Go to Use Cases → "Manage everything on your Page" → Customize → add all permissions |
| Posts work for you but not others | App is in Development mode → switch to Live |
| "Insufficient developer role" | Add account as Instagram Tester in App Roles |
| Channel connects but posts fail | Advanced permissions not approved → submit for App Review |

---

## Checklist

- [ ] Developer account created
- [ ] App created with Business portfolio
- [ ] Facebook Login product added
- [ ] Redirect URIs configured
- [ ] App Domains, Privacy Policy, Category filled in
- [ ] All permissions requested with screencasts
- [ ] Business verification submitted
- [ ] Instagram Business/Creator account linked (if needed)
- [ ] App set to Live mode
- [ ] Credentials copied to Postiz
- [ ] Channel connected in Postiz
