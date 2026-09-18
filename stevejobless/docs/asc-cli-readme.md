# asc-cli — App Store Command Center

**GitHub:** https://github.com/tddworks/asc-cli
**Docs:** http://asccli.app
**License:** MIT

A CLI for App Store Connect — automate builds, releases, TestFlight, subscriptions, and screenshots from your terminal or CI pipeline. Outputs structured JSON so AI agents can drive the full release workflow.

## Quick Start

```bash
brew install asccli

asc auth login \
  --key-id YOUR_KEY_ID \
  --issuer-id YOUR_ISSUER_ID \
  --private-key-path ~/.asc/AuthKey_XXXXXX.p8 \
  --name personal

asc apps list          # find your app ID
asc init --app-id <id> # pin it — skip --app-id on every future command
```

## Features

| Category | What you can do |
| --- | --- |
| Apps & Versions | List apps, create versions, link builds, submit for App Store review |
| Builds | Archive Xcode projects, export IPA/PKG, upload to App Store Connect, distribute to TestFlight |
| Metadata | Update What's New, description, and keywords per locale |
| Screenshots | Create screenshot sets and upload images |
| TestFlight | Manage beta groups, testers, beta review submissions |
| Monetization | IAPs, subscriptions, intro offers, promotional offers, offer codes |
| Code Signing | Bundle IDs, certificates, devices, provisioning profiles |
| Customer Reviews | Read and respond to customer reviews |
| Game Center | Manage achievements and leaderboards |
| Plugins | Install executable plugins for custom event handlers |
| Reports | Sales, subscription, installs, and financial reports |
| Iris (Private API) | Cookie-based auth for create apps, list apps, Resolution Center |
| AI Agents | JSON output with CAEOAS affordances — agents navigate without knowing the command tree |

## Authentication

```bash
asc auth login \
  --key-id YOUR_KEY_ID \
  --issuer-id YOUR_ISSUER_ID \
  --private-key-path ~/.asc/AuthKey_XXXXXX.p8

asc auth update --vendor-number 88012345
asc auth list
asc auth use work
asc auth check
asc auth logout
```

Credentials saved to `~/.asc/credentials.json`. Environment variable alternative:
```bash
export ASC_KEY_ID="YOUR_KEY_ID"
export ASC_ISSUER_ID="YOUR_ISSUER_ID"
export ASC_PRIVATE_KEY_PATH="~/.asc/AuthKey_XXXXXX.p8"
```

## Command Reference

### Apps & Versions
```bash
asc apps list
asc versions list --app-id <id>
asc versions create --app-id <id> --version <v> --platform ios
asc versions set-build --version-id <id> --build-id <id>
asc versions submit --version-id <id>
```

### Builds & TestFlight
```bash
asc builds list [--app-id <id>]
asc builds archive --scheme MyApp --upload --app-id <id> --version 1.0.0 --build-number 42
asc builds upload --app-id <id> --file MyApp.ipa --version 1.0.0 --build-number 42
asc testflight groups list --app-id <id>
asc testflight testers add --beta-group-id <id> --email user@example.com
```

### Monetization
```bash
asc iap list --app-id <id>
asc iap create --app-id <id> --reference-name "Gold Coins" --product-id "com.app.gold" --type consumable
asc subscription-groups create --app-id <id> --reference-name "Premium"
asc subscriptions create --group-id <gid> --name "Monthly" --product-id "com.app.monthly" --period ONE_MONTH
```

### Code Signing
```bash
asc bundle-ids list --platform ios --identifier com.example.app
asc certificates list --type IOS_DISTRIBUTION
asc devices list --platform ios
asc profiles list --type IOS_APP_STORE
```

### Reports
```bash
asc sales-reports download --report-type SALES --sub-type SUMMARY --frequency DAILY
asc finance-reports download --report-type FINANCIAL --region-code US --report-date 2024-01
```

## Design: CAEOAS

REST has HATEOAS — responses embed URLs. This CLI has CAEOAS (Commands As the Engine Of Application State): responses embed ready-to-run CLI commands.

```json
{
  "id": "v1",
  "versionString": "2.1.0",
  "state": "PREPARE_FOR_SUBMISSION",
  "affordances": {
    "checkReadiness": "asc versions check-readiness --version-id v1",
    "submitForReview": "asc versions submit --version-id v1"
  }
}
```

## SPM Usage

```swift
dependencies: [
    .package(url: "https://github.com/tddworks/asc-cli.git", from: "0.1.0"),
]
```

## Requirements

- macOS 13+
- App Store Connect API key
- Swift 6.2+ (only for building from source)
