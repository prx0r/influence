# GitHub — username rules (official)
Source: https://docs.github.com (REST users endpoint documented 200/404)

## Acceptable names
- ≤39 chars, alphanumerics + hyphens. Cannot begin/end with hyphen (reserved patterns).
- Signup/change UI is the claim authority, not the API.

## Our method
`GET api.github.com/users/{u}` → 200 + login match = TAKEN; 404 = NOT_FOUND
with EMU note (Enterprise Managed Users 404 to unauthorized viewers — GitHub's
own documented counterexample to 404-means-free).
- 403/429 (shared-IP budget) → UNKNOWN, KV-cached.
- Never emit AVAILABLE from this endpoint.
