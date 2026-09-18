# TikTok Developer API Setup

**Docs:** https://developers.tiktok.com/doc/overview
**Portal:** https://developers.tiktok.com

## Register Your App

1. Create a TikTok developer account at [signup page](https://developers.tiktok.com)
2. Create or join an organization
3. Log in → Profile icon → **Manage apps**
4. Click **Connect an app**
5. Select app owner (organization or individual account)
6. Fill in app information and add products
7. Submit for review

## App Page Navigation

- **Info icon**: Display App ID and Ownership
- **Production/Sandbox toggle**: Sandbox for testing without review
- **URL properties**: Verify URLs for Content Posting API
- **History**: Changelog and review comments
- **More Options**: Transfer ownership or delete

## App Configuration

### Credentials
- **Client key**: For API authentication
- **Client secret**: For API authentication (keep secure)

### Platforms
- **Web/Desktop**: Requires official website URL
- **Android**: Package name, Play Store URL, app signature
- **iOS**: App Store URL, Bundle ID

### Products
Click **Add products** to add integrations:
- Login Kit
- Share Kit
- Content Posting API
- Display API
- Research API

### Scopes
Configure access to specific data/actions per product.

## Redirect URIs

- **Web/Desktop**: Standard URL
- **Android**: App Link or Deep Link
- **iOS**: Universal Link (requires Associated Domain capability)

## URL Verification

For apps created after September 9, 2024:
1. Terms of Service URL
2. Privacy Policy URL
3. Web/Desktop URL

Content Posting API upload URL always requires verification.

**Verification methods:**
- By Domain: Enter domain and subdomain
- By URL prefix: Enter full URL, download signature file, upload to URL

## Submit for Review

1. Go to **App review** section
2. Explain how each product/scope works
3. Upload demo video(s) showing end-to-end flow (max 5, 50MB each)
4. Save and submit

## Review Statuses

- **Draft**: Not submitted
- **In review**: Submitted, pending approval
- **Approved**: Live and ready
- **Rejected**: Check feedback for updates

## Sandbox Mode

Testing environment without review submission. For trying integrations without production approval.

## Key APIs

| API | Description |
|-----|-------------|
| Content Posting API | Post videos/photos directly |
| Display API | Access user content |
| Research API | Analyze trends and content |
| Login Kit | OAuth authentication |
| Share Kit | Share to TikTok |
