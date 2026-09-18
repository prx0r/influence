// V4 Engine — Cloudflare authoritative registry check + RDAP fallback
// This is the GOOD part of V4. The landing page was the broken part.
// Key improvements over V3:
//   - Cloudflare /registrar/domain-check API (authoritative, batch of 20)
//   - Status enum instead of confidence scores
//   - IANA RDAP bootstrap (47 TLDs)
//   - Never infer AVAILABLE from failure
//   - Clean proof receipts
// To use: replace cfRegistryCheck/rdapCheck/checkDomains/mkResult in worker
//         and update HTTP handler for /api/check/ endpoints
