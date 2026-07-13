# Metabase API Schema Guide

How to obtain the Metabase API specification for a given version, and how the versioned snapshots in this repo are produced.

## Where the spec comes from

Metabase's API is **not versioned** and can change between releases, so the spec you work against must match the instance's version. There are three sources, in order of convenience:

### 1. Committed OpenAPI spec in the source tree (no auth) — preferred

Starting around **v0.60**, Metabase commits a generated OpenAPI 3.1 spec to its own repository at `docs/api.json`. It needs no running instance and no credentials — download it straight from GitHub for the exact tag:

```bash
curl -sL https://raw.githubusercontent.com/metabase/metabase/v0.60.2/docs/api.json -o openapi.json
```

This is the source `scripts/fetch_api_docs.py` uses for newer versions (see below). Older tags (e.g. `v1.48.2`) do **not** have this file.

### 2. Live OpenAPI endpoint (v0.50+, needs auth)

Metabase 0.50 and later expose the same spec at runtime:

```
GET /api/docs/openapi.json          # the spec (JSON)
GET /api/docs/                       # interactive API explorer (Scalar UI)
```

Both require an authenticated session or API key:

```bash
# session auth
curl -H 'X-Metabase-Session: <session_id>' https://your-metabase.com/api/docs/openapi.json -o openapi.json

# API-key auth (v0.49+, admin must enable)
curl -H 'x-api-key: mb_YOUR_KEY' https://your-metabase.com/api/docs/openapi.json -o openapi.json
```

### 3. Per-endpoint markdown in the source tree (older versions)

Older Metabase versions have no OpenAPI spec at all, but they ship human-readable per-endpoint markdown under `docs/api/` in the source tree (`card.md`, `dashboard.md`, `session.md`, …, plus an `ee/` subdirectory for enterprise endpoints). Download them per tag from GitHub — this is the source `scripts/fetch_api_docs.py` uses for older versions.

## Versioned docs in this repo

The `docs/api/` directory (gitignored) holds one subdirectory per Metabase version this CLI cares about:

```
docs/api/
├── v48/            # v1.48.2 — per-endpoint markdown copied verbatim (incl. ee/)
└── v60/            # v0.60.2 — openapi.json + generated per-tag markdown
```

Regenerate them with the fetch script (stdlib only, downloads from GitHub, no auth or Metabase instance required):

```bash
uv run python scripts/fetch_api_docs.py all      # or: v48 | v60
```

For a new version, add an entry to the `VERSIONS` table at the top of the script. The `v60`-style markdown is generated from `openapi.json` (grouped by OpenAPI tag) as grep-friendly reference — method, path, summary/description, parameters, and request-body fields — not rendered documentation.

## Checking an instance's version

```bash
curl -s -H 'X-Metabase-Session: <session_id>' https://your-metabase.com/api/session/properties | jq '.version'
# {"date": "2024-01-05", "tag": "v1.48.2", "hash": "e66c075"}
```

The CLI caches this `version.tag` per profile and shows it in `metabase auth status`.

## Removed / deprecated endpoints

- **`GET /api/util/openapi`** — removed in **0.55**. Use `GET /api/docs/openapi.json` instead.

## API changelog

Metabase publishes breaking API changes here — the authoritative reference when moving between versions:

<https://www.metabase.com/docs/latest/developers-guide/api-changelog>

## Authentication methods

Metabase supports two authentication methods for API access.

### Session token (username/password)

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"username": "user@example.com", "password": "secret"}' \
  https://metabase.example.com/api/session
# -> {"id": "session-uuid-here"}

curl -H 'X-Metabase-Session: session-uuid-here' https://metabase.example.com/api/...
```

### API keys (admin-configured)

Created in the Metabase admin UI (People > API Keys), used via the `x-api-key` header. Require Metabase v0.49+ and must be enabled by an admin.

```bash
curl -H 'x-api-key: mb_api_key_here' https://metabase.example.com/api/...
```

## Known issues

- **Missing `responses` field:** some Metabase versions generate OpenAPI specs missing required `responses` fields, tripping strict validators. See [GitHub issue #61303](https://github.com/metabase/metabase/issues/61303).
- **Unversioned API:** the spec reflects the exact state of one instance; endpoints and parameters can change between releases without a version bump.
