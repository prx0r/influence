# GitHub REST API Documentation

Base URL: `https://api.github.com`

Authentication: `Authorization: Bearer <YOUR-TOKEN>` with `Accept: application/vnd.github+json` and `X-GitHub-Api-Version: 2026-03-10`

## List Repositories

```
GET /user/repos
```

Returns repositories for the authenticated user.

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| visibility | string | `all`, `public`, `private` |
| affiliation | string | `owner`, `collaborator`, `organization_member` |
| type | string | `all`, `public`, `private`, `forks`, `sources`, `member` |
| sort | string | `created`, `updated`, `pushed`, `full_name` |
| direction | string | `asc`, `desc` |
| per_page | integer | Results per page (max 100), default 30 |
| page | integer | Page number, default 1 |

### Example

```bash
curl -L -X GET https://api.github.com/user/repos \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json"
```

## List Organization Repositories

```
GET /orgs/{org}/repos
```

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| org | string (required) | Organization name |
| type | string | `all`, `public`, `private`, `forks`, `sources`, `member` |
| sort | string | `created`, `updated`, `pushed`, `full_name` |
| direction | string | `asc`, `desc` |
| per_page | integer | Results per page (max 100), default 30 |
| page | integer | Page number, default 1 |

### Example

```bash
curl -L -X GET https://api.github.com/orgs/ORG/repos \
  -H "Authorization: Bearer $GITHUB_TOKEN"
```

## Get a Repository

```
GET /repos/{owner}/{repo}
```

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| owner | string (required) | Account owner |
| repo | string (required) | Repository name |

### Example

```bash
curl -L -X GET https://api.github.com/repos/OWNER/REPO \
  -H "Authorization: Bearer $GITHUB_TOKEN"
```

## Create a Repository

```
POST /user/repos
```

### Body Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| name | string (required) | Repository name |
| description | string | Short description |
| homepage | string | URL with more info |
| private | boolean | Private repo, default false |
| has_issues | boolean | Enable issues, default true |
| has_projects | boolean | Enable projects, default true |
| has_wiki | boolean | Enable wiki, default true |
| auto_init | boolean | Create initial commit with empty README |
| license_template | string | License keyword (e.g., "mit") |

### Example

```bash
curl -L -X POST https://api.github.com/user/repos \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -d '{
    "name": "my-repo",
    "description": "My new repository",
    "private": false
  }'
```

## Update a Repository

```
PATCH /repos/{owner}/{repo}
```

### Body Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| name | string | Repository name |
| description | string | Short description |
| private | boolean | Make private/public |
| has_issues | boolean | Enable issues |
| has_projects | boolean | Enable projects |
| has_wiki | boolean | Enable wiki |

### Example

```bash
curl -L -X PATCH https://api.github.com/repos/OWNER/REPO \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -d '{"description": "Updated description"}'
```

## Delete a Repository

```
DELETE /repos/{owner}/{repo}
```

```bash
curl -L -X DELETE https://api.github.com/repos/OWNER/REPO \
  -H "Authorization: Bearer $GITHUB_TOKEN"
```

## List Commits

```
GET /repos/{owner}/{repo}/commits
```

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| owner | string (required) | Account owner |
| repo | string (required) | Repository name |
| sha | string | SHA or branch to start from |
| path | string | Filter by file path |
| author | string | Filter by author |
| since | string | ISO 8601 date (YYYY-MM-DDTHH:MM:SSZ) |
| until | string | ISO 8601 date |
| per_page | integer | Results per page (max 100) |
| page | integer | Page number |

### Example

```bash
curl -L -X GET https://api.github.com/repos/OWNER/REPO/commits?per_page=10 \
  -H "Authorization: Bearer $GITHUB_TOKEN"
```

## Get a Commit

```
GET /repos/{owner}/{repo}/commits/{ref}
```

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| owner | string (required) | Account owner |
| repo | string (required) | Repository name |
| ref | string (required) | SHA or branch name |

## List Pull Requests

```
GET /repos/{owner}/{repo}/pulls
```

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| owner | string (required) | Account owner |
| repo | string (required) | Repository name |
| state | string | `open`, `closed`, `all` |
| sort | string | `created`, `updated`, `popularity`, `long-running` |
| direction | string | `asc`, `desc` |
| per_page | integer | Results per page (max 100) |
| page | integer | Page number |

## Create a Pull Request

```
POST /repos/{owner}/{repo}/pulls
```

### Body Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| title | string (required) | PR title |
| head | string (required) | Branch to merge from |
| base | string (required) | Branch to merge into |
| body | string | PR description |

## List Issues

```
GET /repos/{owner}/{repo}/issues
```

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| owner | string (required) | Account owner |
| repo | string (required) | Repository name |
| state | string | `open`, `closed`, `all` |
| labels | string | Comma-separated labels |
| sort | string | `created`, `updated`, `comments` |
| direction | string | `asc`, `desc` |
| per_page | integer | Results per page |
| page | integer | Page number |

## Create an Issue

```
POST /repos/{owner}/{repo}/issues
```

### Body Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| title | string (required) | Issue title |
| body | string | Issue body (Markdown) |
| assignees | array | Usernames to assign |
| labels | array | Label names |

## List Releases

```
GET /repos/{owner}/{repo}/releases
```

## Create a Release

```
POST /repos/{owner}/{repo}/releases
```

### Body Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| tag_name | string (required) | Git tag |
| target_commitish | string | Branch or commit SHA |
| name | string | Release name |
| body | string | Release description |
| draft | boolean | Draft release |
| prerelease | boolean | Pre-release |

## List Branches

```
GET /repos/{owner}/{repo}/branches
```

## List Tags

```
GET /repos/{owner}/{repo}/tags
```

## Repository Dispatch Event

```
POST /repos/{owner}/{repo}/dispatches
```

Triggers a `repository_dispatch` webhook event.

### Body Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| event_type | string (required) | Custom event name (max 100 chars) |
| client_payload | object | JSON payload (max 10 properties, <64KB) |

```bash
curl -L -X POST https://api.github.com/repos/OWNER/REPO/dispatches \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -d '{
    "event_type": "on-demand-test",
    "client_payload": {"unit": false, "integration": true}
  }'
```

## Rate Limiting

- **Authenticated:** 5,000 requests per hour
- **Unauthenticated:** 60 requests per hour

Check rate limit status:
```
GET /rate_limit
```

## Pagination

Most list endpoints use Link header pagination:

```
Link: <https://api.github.com/repos/OWNER/REPO/commits?page=2>; rel="next"
```

Use `per_page` (max 100) and `page` parameters.
