# Metabase API Schema Guide

How to obtain the Metabase API specification for different versions.

## OpenAPI Endpoint (v0.50+)

Metabase versions 0.50 and later expose an OpenAPI 3.0 specification at:

```
GET /api/docs/openapi.json
```

### Download with session authentication

```bash
# 1. Get session token
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"username": "your@email.com", "password": "yourpassword"}' \
  https://your-metabase.com/api/session

# 2. Download spec
curl -H 'X-Metabase-Session: <session_id>' \
  https://your-metabase.com/api/docs/openapi.json -o openapi.json
```

### Download with API key (if configured)

```bash
curl -H 'x-api-key: YOUR_API_KEY' \
  https://your-metabase.com/api/docs/openapi.json -o openapi.json
```

### Interactive API docs

Available at `/api/docs` (served via RapiDoc/Scalar).

## Older Versions (< v0.50)

Older Metabase versions do not have an OpenAPI endpoint. Options:

### Option 1: Download markdown docs from GitHub

The API documentation is available as markdown files in the Metabase repository.

```bash
# For a specific version (e.g., v1.48.2)
VERSION="v1.48.2"

curl -sL "https://github.com/metabase/metabase/archive/refs/tags/${VERSION}.tar.gz" \
  -o /tmp/metabase.tar.gz

tar -xzf /tmp/metabase.tar.gz -C /tmp

# Docs are in:
ls /tmp/metabase-${VERSION#v}/docs/api/
```

This gives you markdown files like:
- `session.md` - Authentication endpoints
- `card.md` - Questions/queries
- `dashboard.md` - Dashboards
- `database.md` - Database connections
- `collection.md` - Collections/folders
- etc.

### Option 2: Browse versioned docs online

Metabase hosts versioned documentation:

```
https://www.metabase.com/docs/v0.48/api
https://www.metabase.com/docs/v0.49/api
https://www.metabase.com/docs/latest/api
```

### Option 3: Community OpenAPI spec

A minimal community-maintained spec exists at:

```bash
curl -o openapi.yaml \
  https://raw.githubusercontent.com/grokify/go-metabase/master/codegen/swagger_spec.yaml
```

**Note:** This is incomplete and may be outdated. Primarily covers endpoints needed for the Go SDK.

## Checking Metabase Version

To check what version a Metabase instance is running:

```bash
# Get session first, then:
curl -s -H 'X-Metabase-Session: <session_id>' \
  https://your-metabase.com/api/session/properties \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('version'))"

# Output example:
# {'date': '2024-01-05', 'tag': 'v1.48.2', 'hash': 'e66c075'}
```

## Deprecated Endpoints

- `GET /api/util/openapi` - Removed in newer versions, use `/api/docs/openapi.json` instead

## Known Issues

1. **Missing `responses` field**: Some Metabase versions generate OpenAPI specs missing required `responses` fields, causing issues with strict OpenAPI validators. See [GitHub issue #61303](https://github.com/metabase/metabase/issues/61303).

2. **API not versioned**: Metabase's API is not versioned and may change between releases. The spec reflects the current state of the specific instance.

## Authentication Methods

Metabase supports two authentication methods for API access:

### 1. Session Token (username/password)

```bash
# Login
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"username": "user@example.com", "password": "secret"}' \
  https://metabase.example.com/api/session

# Response: {"id": "session-uuid-here"}

# Use in subsequent requests
curl -H 'X-Metabase-Session: session-uuid-here' \
  https://metabase.example.com/api/...
```

### 2. API Keys (admin-configured)

API keys can be created in Metabase admin UI (People > API Keys). Use with header:

```bash
curl -H 'x-api-key: mb_api_key_here' \
  https://metabase.example.com/api/...
```

**Note:** API keys require Metabase v0.49+ and must be enabled by an admin.
