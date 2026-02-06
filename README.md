# metabasecli

A command-line interface for Metabase, designed for both humans and AI agents.

## Features

- **Database exploration** - List databases, schemas, tables, and fields
- **Collection management** - Browse and search collections with tree visualization
- **Card/Question operations** - List, run, create, update, and export saved questions
- **Dashboard management** - Export dashboards with all referenced cards, import, and manage revisions
- **Search** - Search across all Metabase entities
- **URL resolution** - Parse Metabase URLs to understand what entity they reference

## Installation

First clone the repository, then:

```bash
# Install globally with uv (editable mode)
uv tool install -e .
```

Editable mode means updates are automatic after `git pull` - no reinstall needed.

## Configuration

### Interactive Login

```bash
# Login interactively (prompts for auth method)
metabase auth login
```

Supports three authentication methods:
- **API Key** - Recommended for automation (requires Metabase 0.49+)
- **Session ID** - Use an existing session token
- **Credentials** - Username/password (session auto-refreshes when expired)

Configuration is stored at `~/.config/metabasecli/config.toml`.

### Environment Variables

| Variable | Description |
|----------|-------------|
| `METABASE_URL` | Metabase instance URL |
| `METABASE_API_KEY` | API key for authentication |
| `METABASE_SESSION_ID` | Session token |
| `METABASE_USERNAME` | Username for credential auth |
| `METABASE_PASSWORD` | Password for credential auth |

### Multiple Profiles

```bash
# Login to a specific profile
metabase auth login --profile production

# Use a specific profile
metabase --profile production databases list
```

## Usage

### Global Options

```bash
metabase --profile=prod <command>  # Use specific profile
metabase --verbose <command>       # Enable debug logging
metabase --help                    # Show help
```

### Authentication

```bash
# Login interactively
metabase auth login

# Check authentication status
metabase auth status

# Show current token (for debugging)
metabase auth token

# Logout
metabase auth logout
```

### Databases

```bash
# List all databases
metabase databases list

# Get database details
metabase databases get 1

# Get full metadata (schemas, tables, fields)
metabase databases metadata 1

# List schemas
metabase databases schemas 1

# JSON output
metabase databases list --json
```

### Collections

```bash
# Show collection tree from root
metabase collections tree

# Search collections by name
metabase collections tree --search "Sales"

# Control depth of children shown
metabase collections tree --search "Reports" --levels 2

# Get collection details
metabase collections get 123

# List items in a collection
metabase collections items 123
metabase collections items 123 --models card,dashboard

# JSON output
metabase collections tree --json
```

### Cards (Questions)

```bash
# List all cards
metabase cards list

# Filter by collection
metabase cards list --collection-id 123

# Get card details
metabase cards get 456

# Run a card and export results (JSON + CSV)
metabase cards run 456
# Outputs to /tmp/metabase-<timestamp>/card-456-data.json and .csv

# Import a card from JSON file
metabase cards import --file card-definition.json

# Update an existing card
metabase cards import --file card-definition.json --id 456

# Archive a card
metabase cards archive 456

# Delete a card
metabase cards delete 456 --force
```

### Dashboards

```bash
# List all dashboards
metabase dashboards list

# Get dashboard details
metabase dashboards get 789

# Export dashboard with all referenced cards
metabase dashboards export 789
# Creates /tmp/metabase-<timestamp>/ with:
#   - manifest.json
#   - dashboard-789.json
#   - card-*.json (one per referenced card)

# Import a dashboard
metabase dashboards import --file dashboard-definition.json

# Update an existing dashboard
metabase dashboards import --file dashboard-definition.json --id 789

# View revision history
metabase dashboards revisions 789

# Revert to a previous revision
metabase dashboards revert 789 12345

# Archive/delete
metabase dashboards archive 789
metabase dashboards delete 789 --force
```

### Search

```bash
# Search across all entities
metabase search "revenue"

# Filter by type
metabase search "sales" --models dashboard,card

# Filter by collection
metabase search "report" --collection-id 123

# Include archived items
metabase search "old" --archived

# JSON output
metabase search "metrics" --json
```

### URL Resolution

```bash
# Resolve a Metabase URL to understand what it references
metabase resolve "https://metabase.example.com/question/123"
metabase resolve "https://metabase.example.com/dashboard/456-sales-dashboard"
metabase resolve "/collection/789"

# JSON output (default for this command)
metabase resolve "https://metabase.example.com/question/123" --json
```

## Output Formats

### Text Output (Default)

Human-readable format with tables and trees:

```
Databases:
  ID  Name              Engine
  1   Production DB     postgres
  2   Analytics DW      snowflake
```

### JSON Output

Machine-readable format for AI agents:

```json
{
  "success": true,
  "data": [...],
  "meta": {
    "total": 2
  }
}
```

## File Export Convention

All exports are written to timestamped directories:

```
/tmp/metabase-20250205-143022/
├── manifest.json
├── dashboard-123.json
├── card-456.json
└── card-789.json
```

## Developing

### Setup

```bash
# Clone and install dependencies
git clone <repo>
cd metabasecli
uv sync
```

### Running

```bash
# Run the CLI
uv run metabase --help

# Run a command
uv run metabase databases list
```

### Linting and Formatting

```bash
# Format code
uv run ruff format src/

# Lint code
uv run ruff check src/

# Lint and auto-fix
uv run ruff check --fix src/
```

### Project Structure

```
src/metabasecli/
├── __init__.py         # Package version
├── cli.py              # Main CLI entry point
├── config.py           # Configuration loading/saving
├── constants.py        # Shared constants
├── context.py          # CLI context
├── logging.py          # Logging setup
├── output.py           # Output formatting and file export
├── utils.py            # Shared utilities
├── client/             # API client modules
│   ├── base.py         # Base client with session management
│   ├── auth.py         # Authentication API
│   ├── cards.py        # Cards API
│   ├── collections.py  # Collections API
│   ├── dashboards.py   # Dashboards API
│   ├── databases.py    # Databases API
│   └── search.py       # Search API
├── commands/           # CLI command modules
│   ├── auth.py         # Auth commands
│   ├── cards.py        # Card commands
│   ├── collections.py  # Collection commands
│   ├── dashboards.py   # Dashboard commands
│   ├── databases.py    # Database commands
│   ├── resolve.py      # URL resolution
│   └── search.py       # Search command
└── models/             # Data models
    ├── auth.py         # Auth config models
    ├── card.py         # Card models
    ├── collection.py   # Collection models
    ├── dashboard.py    # Dashboard models
    └── database.py     # Database models
```

## License

MIT
