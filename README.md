# metabasecli

A command-line interface for Metabase, designed for both humans and AI agents.

## Quick Start

```bash
# Install
uv tool install -e .

# Login
metabase auth login

# Explore
metabase databases list
metabase collections tree --search "Sales"
metabase search "revenue report"

# Export a dashboard with all its cards
metabase dashboards export 123
```

## Terminology

Metabase uses different terms in different contexts:

| CLI Command | Metabase UI | API | Description |
|-------------|-------------|-----|-------------|
| `cards` | Questions | `/api/card` | Saved queries with visualization settings |
| `dashboards` | Dashboards | `/api/dashboard` | Collections of cards arranged in a layout |
| `collections` | Collections | `/api/collection` | Folders that organize cards and dashboards |
| `databases` | Databases | `/api/database` | Data source connections |

**Aliases:** `metabase queries` and `metabase questions` are aliases for `metabase cards`.

## Installation

```bash
# Clone and install globally with uv (editable mode)
git clone <repo>
cd metabasecli
uv tool install -e .
```

Editable mode means changes are automatic after `git pull` - no reinstall needed.

## Claude Code

This repository is a [Claude Code](https://docs.anthropic.com/en/docs/claude-code) plugin marketplace. The plugin ships a skill that teaches Claude how to use the `metabase` CLI. It does not install the CLI itself — install that first, see [Installation](#installation).

```bash
claude plugin marketplace add fprochazka/metabasecli --scope user
claude plugin install metabasecli@fprochazka-metabasecli --scope user
```

To upgrade after a new release:

```bash
claude plugin marketplace update fprochazka-metabasecli
claude plugin update metabasecli@fprochazka-metabasecli
```

The skill's `allowed-tools` frontmatter auto-allows read-only commands (`search`, `resolve`, `databases list`, `collections tree`, `cards get`, `dashboards export`, etc.) and auth/help commands. Write operations (`cards create`, `dashboards import`, etc.) require manual approval. To let the skill load without a prompt, add it to `~/.claude/settings.json`:

```json
{
  "permissions": {
    "allow": [
      "Skill(metabasecli)"
    ]
  }
}
```

## Authentication

### Interactive Login

```bash
metabase auth login
```

Prompts to choose an authentication method:

| Method | Best For | Notes |
|--------|----------|-------|
| **API Key** | Automation, CI/CD | Requires Metabase 0.49+, admin must enable |
| **Credentials** | Interactive use | Session auto-refreshes when expired |
| **Session ID** | Debugging | Manual token, no auto-refresh |

### Environment Variables

Environment variables override config file settings:

| Variable | Description |
|----------|-------------|
| `METABASE_URL` | Metabase instance URL (e.g., `https://metabase.example.com`) |
| `METABASE_API_KEY` | API key (starts with `mb_`) |
| `METABASE_SESSION_ID` | Session token (UUID) |
| `METABASE_USERNAME` | Email for credential auth |
| `METABASE_PASSWORD` | Password for credential auth |

### Multiple Profiles

```bash
# Login to different instances
metabase auth login --profile production
metabase auth login --profile staging

# Use a specific profile
metabase --profile staging databases list
```

Config stored at `~/.config/metabasecli/config.toml`. Alongside it, `~/.config/metabasecli/cache.json` caches informational per-profile instance metadata (currently the detected Metabase version); it is safe to delete and is regenerated on the next `auth login`/`auth status`.

### Check Auth Status

```bash
metabase auth status        # Shows current user, instance version, and auth method
metabase auth token         # Prints current token (for debugging)
metabase auth logout        # Clear stored credentials
```

## Commands

### Global Options

```bash
metabase --profile <name> <command>   # Use specific profile
metabase --verbose <command>          # Debug logging to stderr
metabase --json <command>             # JSON output (most commands)
metabase --help                       # Show help
metabase --version                    # Show version
```

### Databases

```bash
metabase databases list                    # List all databases
metabase databases get <id>                # Get database details
metabase databases metadata <id>           # Full metadata: schemas, tables, fields
metabase databases schemas <id>            # List schema names
```

### Collections

```bash
# Tree view with search
metabase collections tree                          # From root
metabase collections tree --search "Sales"         # Filter by name
metabase collections tree --search "Q4" --levels 2 # Show 2 levels of children

# Collection details
metabase collections get <id>                      # Get collection info
metabase collections items <id>                    # List items in collection
metabase collections items <id> --models card,dashboard  # Filter by type
```

The tree command always shows the path from matched collections up to root, plus N levels of children (default: 1).

### Cards (Questions/Queries)

```bash
# List and get
metabase cards list                        # List all cards
metabase cards list --collection-id 123    # Filter by collection
metabase cards get <id>                    # Get card definition

# Run query and export results
metabase cards run <id>
# Creates /tmp/metabase-<timestamp>/
#   card-<id>-results.json   (query results as JSON)
#   card-<id>-results.csv    (query results as CSV)

# Create or update
metabase cards import --file card.json              # Create new card
metabase cards import --file card.json --id 456     # Update existing
cat card.json | metabase cards import --file -      # From stdin

# Delete
metabase cards archive <id>                # Soft delete (recoverable)
metabase cards delete <id> --force         # Permanent delete
```

### Dashboards

```bash
# List and get
metabase dashboards list                   # List all dashboards
metabase dashboards list --collection-id 123
metabase dashboards get <id>               # Get dashboard with cards

# Export (dashboard + all referenced cards)
metabase dashboards export <id>
# Creates /tmp/metabase-<timestamp>/
#   dashboard-<id>.json   (dashboard definition)
#   card-<id>.json        (one per referenced card)

# Create or update
metabase dashboards import --file dashboard.json           # Create new
metabase dashboards import --file dashboard.json --id 789  # Update existing

# Revisions
metabase dashboards revisions <id>             # List revision history
metabase dashboards revert <id> <revision-id>  # Revert to revision

# Delete
metabase dashboards archive <id>           # Soft delete
metabase dashboards delete <id> --force    # Permanent delete
```

### Search

```bash
metabase search "revenue"                      # Search all entities
metabase search "sales" --models dashboard,card  # Filter by type
metabase search "report" --collection-id 123   # Within collection
metabase search "old" --archived               # Include archived
```

Searchable models: `card`, `dashboard`, `collection`, `table`, `database`

### URL Resolution

Parse a Metabase URL to get entity information:

```bash
metabase resolve "https://metabase.example.com/question/123"
metabase resolve "https://metabase.example.com/dashboard/456-sales"
metabase resolve "/collection/789"
```

Useful for AI agents that receive Metabase links and need to understand what they reference.

### API (raw requests)

An escape hatch for endpoints without a dedicated command. Sends a raw request and prints the server's response verbatim (no `{success, data}` envelope), modeled on `gh api` / `glab api`:

```bash
metabase api /user/current                             # GET (default method)
metabase api "/search?q=revenue&models=dashboard"      # query string rides inline
metabase api /card -X POST --input card.json           # body from a file (defaults to POST)
cat card.json | metabase api /card --input -           # body from stdin
```

The endpoint may be written as `/card/1`, `card/1`, or `/api/card/1` (all equivalent). The method defaults to `GET`, or to `POST` when `--input` is given; override it with `-X/--method`. Response bodies are pretty-printed when JSON. On a non-2xx status the body is still printed, an `HTTP <status>` note goes to stderr, and the exit code is 1.

### Snapshot (whole-instance mirror)

Dumps the entire instance's shared collection content into a deterministic, git-diffable local file tree. The primary use case is a **read-only archive for AI agents** to grep as local files, and a periodic versioned mirror (run on a schedule, commit and push the output dir to a dedicated repo for history). Restore is explicitly a non-goal; actionability is — every dumped object retains its `id` and a `url` pointing back to the live instance so an agent that finds something can act on it.

```bash
metabase snapshot --output <dir>                    # full shared-collection mirror
metabase snapshot --output <dir> --collection-id N  # scope to one subtree (fast)
metabase snapshot --output <dir> --include-personal # also dump personal collections
metabase snapshot --output <dir> --commit           # commit output dir after a clean run
metabase snapshot --output <dir> --commit --push    # commit then push
metabase snapshot --output <dir> --reprocess-only   # re-canonicalize from cache, no network
```

**Flags:**

| Flag | Description |
|------|-------------|
| `--output <dir>` | Directory to write the snapshot tree into. **Required.** |
| `--collection-id N` | Restrict to this collection and its descendants. Useful for fast, focused runs. |
| `--include-personal` | Include personal collections (default: shared, non-archived only). |
| `--reprocess-only` | Rebuild the tree from the raw cache of a prior full run, skipping all API calls. Errors if the cache is absent. |
| `--commit` | After a clean run, `git add -A` and commit the output dir as `v<timestamp>`. |
| `--push` | `git push` the output dir after committing (output dir must be a git repo). |
| `--json` | Structured JSON output. |

**Output layout** mirrors the collection hierarchy. Directories are named `<id>-<slug>`; each collection gets a `_collection.json`, a `cards/` subdir, and a `dashboards/` subdir. A native-SQL card's SQL is written to a `.sql` companion alongside its `.json`, and the JSON's `dataset_query.native.query` points to that file (`./<id>-<slug>.sql`) instead of inlining the SQL — so the JSON stays readable and the SQL lives once, grep-friendly. Root-level items (no parent collection) land at the tree root:

```
<output>/
├── 42-analytics/
│   ├── _collection.json
│   ├── cards/
│   │   ├── 101-weekly-summary.json
│   │   ├── 102-revenue-by-region.json
│   │   └── 102-revenue-by-region.sql   # native SQL companion
│   ├── dashboards/
│   │   └── 55-executive-overview.json
│   └── 99-finance/                     # nested sub-collection
│       ├── _collection.json
│       └── cards/
│           └── 210-quarterly-costs.json
├── cards/                              # root-level cards (collection_id == null)
└── dashboards/
```

**Determinism and idempotency:** every file is written as `json.dumps(sort_keys=True, indent=2)`. Runtime-churn fields (`view_count`, `last_used_at`, embedded per-run blobs, etc.) are stripped before writing, so re-running on an unchanged instance produces a byte-identical tree and `git diff` stays empty.

**Default scope and scale:** only shared, non-archived collections are fetched by default; personal collections (and nested personal sub-collections) are excluded. `--include-personal` widens the scope. `--collection-id` scopes to a single subtree for focused, fast runs. A full run against a large instance is a slow batch job — expect thousands of per-object API calls. Every fetched body is cached under `<output>/.metabase-snapshot-cache/` (auto-gitignored), enabling `--reprocess-only` to re-run canonicalization from that cache without re-fetching.

**Mirror workflow:** if the output dir is its own git repo, `--commit` versions the snapshot as `v<timestamp>` and `--push` pushes it upstream. Both run only after a fully successful run — a partial mirror with fetch failures is never committed.

## Output Formats

### Human-Readable (Default)

Tables, trees, and formatted text for terminal:

```
Databases:
  ID  Name              Engine
───────────────────────────────
   1  Production DB     postgres
   2  Analytics DW      snowflake
```

### JSON Output (`--json`)

Structured format for automation and AI agents:

```json
{
  "success": true,
  "data": {
    "databases": [
      {"id": 1, "name": "Production DB", "engine": "postgres"},
      {"id": 2, "name": "Analytics DW", "engine": "snowflake"}
    ]
  },
  "meta": {
    "total": 2
  }
}
```

**Error responses:**

```json
{
  "success": false,
  "error": {
    "code": "NOT_FOUND",
    "message": "Card 999 not found"
  }
}
```

Error codes: `NOT_FOUND`, `AUTHENTICATION_ERROR`, `SESSION_EXPIRED`, `API_ERROR`, `VALIDATION_ERROR`

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (see stderr or JSON error) |

## Export File Formats

### Card JSON

Complete card definition including:
- `name`, `description`, `collection_id`
- `dataset_query` - The query (MBQL or native SQL)
- `display` - Visualization type (`table`, `bar`, `line`, `pie`, etc.)
- `visualization_settings` - Chart configuration

### Dashboard JSON

Complete dashboard definition including:
- `name`, `description`, `collection_id`
- `dashcards` - Cards with position (`row`, `col`, `size_x`, `size_y`)
- `parameters` - Dashboard filters
- `tabs` - Dashboard tabs (if any)

## Common Workflows

### AI Agent: Understand a Metabase Link

```bash
# User shares a Metabase URL, agent needs to understand it
metabase resolve "https://metabase.example.com/dashboard/123" --json

# Then explore its contents
metabase dashboards get 123 --json
```

### AI Agent: Find and Modify a Dashboard

```bash
# Search for the dashboard
metabase search "quarterly sales" --models dashboard --json

# Export it for analysis
metabase dashboards export 456

# Read the exported files, make changes, then update
metabase cards import --file /tmp/metabase-xxx/card-789.json --id 789
metabase dashboards import --file /tmp/metabase-xxx/dashboard-456.json --id 456
```

### AI Agent: Create a New Report

```bash
# Find the target collection
metabase collections tree --search "Reports" --json

# Find available data sources
metabase databases list --json
metabase databases metadata 1 --json

# Create the card (query)
metabase cards import --file new-card.json

# Create dashboard and add the card
metabase dashboards import --file new-dashboard.json
```

### Run a Query and Get Results

```bash
# Run and export to files
metabase cards run 123

# Results in /tmp/metabase-<timestamp>/
#   card-123-results.json - structured data
#   card-123-results.csv  - for spreadsheets
```

## Troubleshooting

### "Not authenticated" Error

```bash
metabase auth status   # Check current auth state
metabase auth login    # Re-authenticate
```

### Session Expired

If using credentials auth, sessions auto-refresh. If using session ID auth, you need to manually get a new token.

### API Key Not Working

- Requires Metabase 0.49+
- Admin must enable API keys in Metabase settings
- Key must start with `mb_`

### Command Not Found

```bash
# Reinstall
uv tool install -e /path/to/metabasecli --force
```

## Development

```bash
# Setup
git clone <repo>
cd metabasecli
uv sync

# Run locally
uv run metabase --help

# Lint and format
uv run ruff check src/ --fix
uv run ruff format src/

# Refresh the version-scoped Metabase API docs under docs/api/ (downloads from GitHub)
uv run python scripts/fetch_api_docs.py all
```

See [docs/metabase-api.md](docs/metabase-api.md) for how the API spec is sourced per Metabase version.

### Project Structure

```
src/metabasecli/
├── cli.py              # Entry point, command registration
├── config.py           # Config file loading/saving
├── context.py          # Global CLI context
├── output.py           # JSON/file output helpers
├── client/             # API clients (one per resource)
│   ├── base.py         # HTTP client, auth, session refresh
│   └── *.py            # cards, dashboards, collections, etc.
├── commands/           # CLI commands (one per resource)
│   └── *.py
└── models/             # Dataclasses for API responses
    └── *.py
```

## Compatibility

- **Python:** 3.11+
- **Metabase:** Tested with 0.48 and 0.60; API keys require 0.49+

## License

MIT
