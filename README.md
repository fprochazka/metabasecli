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

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill is available for this project, allowing Claude to use the `metabase` CLI autonomously. See [metabasecli skill](https://github.com/fprochazka/claude-code-plugins/tree/master/plugins/metabasecli) for installation and usage instructions.

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

Config stored at `~/.config/metabasecli/config.toml`.

### Check Auth Status

```bash
metabase auth status        # Shows current user and auth method
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
#   card-<id>-data.json   (query results as JSON)
#   card-<id>-data.csv    (query results as CSV)

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
#   manifest.json         (export metadata)
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

### manifest.json

```json
{
  "export_version": "1.0",
  "exported_at": "2025-02-05T14:30:22Z",
  "metabase_url": "https://metabase.example.com",
  "dashboard_id": 123,
  "files": {
    "dashboard": "dashboard-123.json",
    "cards": ["card-456.json", "card-789.json"]
  }
}
```

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
#   card-123-data.json - structured data
#   card-123-data.csv  - for spreadsheets
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
```

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
- **Metabase:** Tested with 0.48+, API keys require 0.49+

## License

MIT
