# Metabase CLI Structure Proposal

This document outlines the proposed command structure for the Metabase CLI tool, designed to support both human users and LLM agents in managing Metabase resources.

## Design Principles

1. **LLM-Optimized**: Commands return complete, self-contained context to minimize round-trips
2. **JSON Output Preferred**: Machine-readable JSON output for AI agent consumption
3. **Hierarchical Organization**: Commands grouped by resource type with intuitive subcommands
4. **Batched Operations**: Combine related API calls where it reduces complexity
5. **File-Based Exports**: Use timestamped directories in `/tmp/metabase-<timestamp>/` for all file output
6. **Simplicity**: Fewer subcommands, more options - merge similar functionality

---

## Authentication

### Configuration File

Configuration stored in `~/.config/metabase/config.toml`:

```toml
[default]
url = "https://metabase.example.com"

# Authentication method (one of the following):
auth_method = "api_key"  # or "session_id" or "credentials"

# For api_key method:
api_key = "mb_api_key_..."

# For session_id method:
session_id = "your-session-id"

# For credentials method (session_id is auto-managed):
username = "user@example.com"
password = "password"
session_id = "auto-generated-session-id"  # managed by CLI
```

### Environment Variables

Override config file settings:

```bash
METABASE_URL=https://metabase.example.com
METABASE_API_KEY=mb_api_key_...
# OR
METABASE_SESSION_ID=your-session-id
# OR
METABASE_USERNAME=user@example.com
METABASE_PASSWORD=password
```

### Authentication Commands

```
metabase auth login           # Interactive login with auth method selection
metabase auth logout          # Clear stored session
metabase auth status          # Show current auth status and user info
metabase auth token           # Print current session token (for piping)
```

---

## Output Modes

All commands support two output modes:

| Flag | Description |
|------|-------------|
| (default) | Human-readable formatted output using Rich |
| `--json` | Machine-readable JSON output |

JSON output follows a consistent envelope structure:

```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "timestamp": "2026-02-05T18:35:00Z",
    "api_calls": 3
  }
}
```

Error responses:

```json
{
  "success": false,
  "error": {
    "code": "NOT_FOUND",
    "message": "Dashboard with ID 123 not found"
  }
}
```

---

## Command Hierarchy

```
metabase
  |-- auth
  |   |-- login
  |   |-- logout
  |   |-- status
  |   `-- token
  |
  |-- databases
  |   |-- list
  |   |-- get <id>
  |   |-- metadata <id>
  |   `-- schemas <id>
  |
  |-- collections
  |   |-- tree
  |   |-- get <id>
  |   |-- items <id>
  |   |-- create
  |   |-- update <id>
  |   `-- archive <id>
  |
  |-- cards (aliases: queries, questions)
  |   |-- list
  |   |-- get <id>
  |   |-- run <id>
  |   |-- import
  |   |-- archive <id>
  |   `-- delete <id>
  |
  |-- dashboards
  |   |-- list
  |   |-- get <id>
  |   |-- export <id>
  |   |-- import
  |   |-- archive <id>
  |   |-- delete <id>
  |   |-- revisions <id>
  |   `-- revert <id> <revision_id>
  |
  |-- search <query>
  |
  `-- resolve <url>
```

---

## Detailed Command Specifications

### `metabase auth`

#### `metabase auth login`

Authenticate with Metabase and store credentials/session.

**Behavior:**
1. Prompts user to select authentication method: `api_key`, `session_id`, or `credentials`
2. Based on selection, prompts for the required values
3. Validates the authentication works
4. Saves values to config file

For `credentials` method:
- CLI obtains a session_id from the API and persists it in config
- On subsequent requests, uses the stored session_id
- If session expires, automatically refreshes using stored credentials

**Options:**
- `--url <url>` - Metabase instance URL
- `--method <method>` - Auth method: api_key, session_id, credentials (prompts if omitted)
- `--profile <name>` - Profile name for storing credentials (default: "default")

**Example:**
```bash
metabase auth login --url https://metabase.example.com
# Prompts:
# Select authentication method:
#   1. api_key
#   2. session_id
#   3. credentials
# Enter choice: 3
# Username: user@example.com
# Password: ********
# Authenticating... done
# Session saved to ~/.config/metabase/config.toml
```

#### `metabase auth status`

Show current authentication status.

**Output (human):**
```
Authenticated as: user@example.com
Instance: https://metabase.example.com
Auth method: credentials
Session valid until: 2026-02-06T18:35:00Z
```

**Output (JSON):**
```json
{
  "success": true,
  "data": {
    "authenticated": true,
    "auth_method": "credentials",
    "user": {
      "id": 1,
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "is_superuser": true
    },
    "instance_url": "https://metabase.example.com"
  }
}
```

---

### `metabase databases`

#### `metabase databases list`

List all databases the current user has access to.

**Options:**
- `--include-tables` - Include table information
- `--json` - JSON output

**Example:**
```bash
metabase databases list --json
```

**Output (JSON):**
```json
{
  "success": true,
  "data": {
    "databases": [
      {
        "id": 1,
        "name": "Production",
        "engine": "postgres",
        "tables_count": 45
      }
    ]
  }
}
```

#### `metabase databases get <id>`

Get database details.

**Arguments:**
- `id` - Database ID (required)

**Options:**
- `--include-tables` - Include tables
- `--include-fields` - Include tables and fields
- `--json` - JSON output

#### `metabase databases metadata <id>`

Get complete database metadata including all tables and fields.

**Arguments:**
- `id` - Database ID (required)

**Options:**
- `--include-hidden` - Include hidden tables and fields
- `--json` - JSON output

**Output:** Complete database schema information useful for query construction.

#### `metabase databases schemas <id>`

List all schemas in a database.

**Arguments:**
- `id` - Database ID (required)

---

### `metabase collections`

#### `metabase collections tree`

**This is a key command for LLM agents.** Display collection hierarchy as a tree, with optional filtering.

**Behavior:**
- If no filtering options given, matched results are root level nodes
- Always renders from matched nodes up to root (showing path context)
- Renders specified levels deep from matched results

**Options:**
- `--search <query>` - Filter collections by name
- `--levels <n>` - How many levels deep to render from matched results (default: 1 = one level of children)
- `--exclude-archived` - Exclude archived (default: true)
- `--json` - JSON output

**Example (no filter - shows from root):**
```bash
metabase collections tree
```

**Output (human):**
```
Root Collection
  +-- Analytics
  |   +-- Sales Reports
  |   `-- Marketing
  +-- Engineering
  `-- Personal Collections
```

**Example (with search):**
```bash
metabase collections tree --search "sales" --levels 2
```

**Output (human):**
```
Search Results (2 matches):

Root Collection
  +-- Analytics
  |   +-- [MATCH] Sales Reports
  |   |   +-- Monthly          (child)
  |   |   |   +-- 2025         (grandchild)
  |   |   |   `-- 2026         (grandchild)
  |   |   `-- Quarterly        (child)
  |   `-- Marketing
  |       `-- [MATCH] Sales Metrics
  |           +-- Regional     (child)
  |           `-- Product      (child)

Matches:
  - Sales Reports (id: 2, path: /Analytics/Sales Reports)
  - Sales Metrics (id: 15, path: /Analytics/Marketing/Sales Metrics)
```

**Output (JSON):**
```json
{
  "success": true,
  "data": {
    "query": "sales",
    "levels": 2,
    "matches": [
      {
        "id": 2,
        "name": "Sales Reports",
        "path": ["Analytics", "Sales Reports"],
        "path_ids": [1, 2],
        "children": [
          {
            "id": 3,
            "name": "Monthly",
            "children": [
              {"id": 10, "name": "2025"},
              {"id": 11, "name": "2026"}
            ]
          },
          {"id": 4, "name": "Quarterly", "children": []}
        ]
      }
    ],
    "tree": {
      "id": "root",
      "name": "Root Collection",
      "children": [
        {
          "id": 1,
          "name": "Analytics",
          "children": [
            {
              "id": 2,
              "name": "Sales Reports",
              "is_match": true,
              "children": [...]
            }
          ]
        }
      ]
    }
  }
}
```

#### `metabase collections get <id>`

Get collection details.

**Arguments:**
- `id` - Collection ID (required, use "root" for root collection)

**Options:**
- `--json` - JSON output

#### `metabase collections items <id>`

List items in a collection.

**Arguments:**
- `id` - Collection ID (required, use "root" for root collection)

**Options:**
- `--models <types>` - Filter by type: card, dashboard, collection, dataset, pulse
- `--archived` - Show archived items
- `--sort-by <column>` - Sort by: name, last_edited_at, last_edited_by, model
- `--sort-dir <dir>` - Sort direction: asc, desc
- `--json` - JSON output

**Example:**
```bash
metabase collections items 42 --models card,dashboard
```

#### `metabase collections create`

Create a new collection.

**Options:**
- `--name <name>` - Collection name (required)
- `--description <text>` - Description
- `--parent-id <id>` - Parent collection ID (omit for root)
- `--json` - JSON output

#### `metabase collections update <id>`

Update a collection.

**Arguments:**
- `id` - Collection ID (required)

**Options:**
- `--name <name>` - New name
- `--description <text>` - New description
- `--parent-id <id>` - Move to new parent
- `--json` - JSON output

#### `metabase collections archive <id>`

Archive a collection.

**Arguments:**
- `id` - Collection ID (required)

---

### `metabase cards`

Aliases: `queries`, `questions`

Cards represent saved questions/queries in Metabase.

#### `metabase cards list`

List all cards.

**Options:**
- `--filter <type>` - Filter: all, mine, bookmarked, archived, database, table, using_model
- `--collection-id <id>` - Filter by collection
- `--database-id <id>` - Filter by database (requires --filter=database)
- `--json` - JSON output

#### `metabase cards get <id>`

Get card details including full query definition.

**Arguments:**
- `id` - Card ID (required)

**Options:**
- `--json` - JSON output

**Output (JSON):**
```json
{
  "success": true,
  "data": {
    "id": 123,
    "name": "Monthly Sales",
    "description": "Sales aggregated by month",
    "collection_id": 42,
    "collection": {
      "id": 42,
      "name": "Sales Reports",
      "path": ["Analytics", "Sales Reports"]
    },
    "database_id": 1,
    "dataset_query": {
      "type": "native",
      "native": {
        "query": "SELECT date_trunc('month', created_at) as month, SUM(amount) as total FROM orders GROUP BY 1",
        "template-tags": {}
      },
      "database": 1
    },
    "display": "bar",
    "visualization_settings": {...},
    "parameters": [...],
    "created_at": "2026-01-15T10:00:00Z",
    "updated_at": "2026-02-01T14:30:00Z"
  }
}
```

#### `metabase cards run <id>`

Execute a card's query and return results. Always outputs both JSON and CSV formats.

**Arguments:**
- `id` - Card ID (required)

**Options:**
- `--parameters <json>` - Query parameters as JSON
- `--limit <n>` - Limit rows (default: 2000)
- `--json` - JSON output (for metadata)

**Behavior:**
1. Fetches query results as JSON from API
2. Converts to both JSON and CSV formats
3. Writes both files to `/tmp/metabase-<timestamp>/`
4. Shows both filepaths in output

**Output (human):**
```
Executing card 123: Monthly Sales
Rows returned: 24

Output files:
  - /tmp/metabase-20260205-183500/card-123-results.json
  - /tmp/metabase-20260205-183500/card-123-results.csv
```

**Output (JSON):**
```json
{
  "success": true,
  "data": {
    "card_id": 123,
    "card_name": "Monthly Sales",
    "row_count": 24,
    "files": {
      "json": "/tmp/metabase-20260205-183500/card-123-results.json",
      "csv": "/tmp/metabase-20260205-183500/card-123-results.csv"
    }
  }
}
```

#### `metabase cards import`

Import a card from a JSON definition file. Creates a new card or updates an existing one.

**Options:**
- `--file <path>` - Path to card JSON file (or use stdin)
- `--id <id>` - Card ID to update (if omitted, creates new card)
- `--collection-id <id>` - Target collection (overrides file)
- `--database-id <id>` - Target database (overrides file, required if different instance)
- `--json` - JSON output

**Examples:**
```bash
# Create new card from file
metabase cards import --file /tmp/metabase-20260205-183500/card-123.json

# Update existing card
metabase cards import --file /tmp/metabase-20260205-183500/card-123.json --id 456

# From stdin
cat card-definition.json | metabase cards import

# Update from stdin
cat card-definition.json | metabase cards import --id 456
```

**Output (JSON only - no human-readable output needed):**
```json
{
  "success": true,
  "data": {
    "id": 456,
    "name": "Monthly Sales",
    "action": "updated"
  }
}
```

#### `metabase cards archive <id>`

Archive a card (soft delete).

**Arguments:**
- `id` - Card ID (required)

#### `metabase cards delete <id>`

Permanently delete a card.

**Arguments:**
- `id` - Card ID (required)

**Options:**
- `--force` - Skip confirmation

---

### `metabase dashboards`

#### `metabase dashboards list`

List all dashboards.

**Options:**
- `--collection-id <id>` - Filter by collection
- `--json` - JSON output

#### `metabase dashboards get <id>`

Get dashboard with all dashcard definitions.

**Arguments:**
- `id` - Dashboard ID (required)

**Options:**
- `--include-cards` - Include full card definitions for all referenced cards
- `--json` - JSON output

**Output (JSON with --include-cards):**
```json
{
  "success": true,
  "data": {
    "id": 456,
    "name": "Sales Overview",
    "description": "Key sales metrics",
    "collection_id": 42,
    "collection": {
      "id": 42,
      "name": "Sales Reports",
      "path": ["Analytics", "Sales Reports"]
    },
    "parameters": [...],
    "dashcards": [
      {
        "id": 1001,
        "card_id": 123,
        "row": 0,
        "col": 0,
        "size_x": 6,
        "size_y": 4,
        "parameter_mappings": [...],
        "visualization_settings": {...}
      }
    ],
    "tabs": [...],
    "referenced_cards": {
      "123": {
        "id": 123,
        "name": "Monthly Sales",
        "dataset_query": {...},
        "display": "bar"
      }
    },
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-02-05T12:00:00Z"
  }
}
```

#### `metabase dashboards export <id>`

**This is a key command for LLM agents.** Export a complete dashboard with all referenced cards.

**Arguments:**
- `id` - Dashboard ID (required)

**Options:**
- `--json` - Return file paths as JSON

**Behavior:**
1. Fetches dashboard with full details
2. Identifies all cards referenced by dashcards
3. Fetches each referenced card
4. Creates files in `/tmp/metabase-<timestamp>/`:
   - `dashboard-<id>.json` - Dashboard definition
   - `card-<id>.json` - One file per referenced card
   - `manifest.json` - Index of all exported files

**Output Directory Structure:**
```
/tmp/metabase-20260205-183500/
  +-- manifest.json
  +-- dashboard-456.json
  +-- card-123.json
  +-- card-124.json
  `-- card-125.json
```

**manifest.json:**
```json
{
  "export_version": "1.0",
  "export_timestamp": "2026-02-05T18:35:00Z",
  "source": {
    "instance_url": "https://metabase.example.com"
  },
  "dashboard": {
    "id": 456,
    "name": "Sales Overview",
    "file": "dashboard-456.json"
  },
  "cards": [
    {"id": 123, "name": "Monthly Sales", "file": "card-123.json"},
    {"id": 124, "name": "Sales by Region", "file": "card-124.json"},
    {"id": 125, "name": "Top Products", "file": "card-125.json"}
  ]
}
```

**Human-readable output:**
```
Exporting dashboard 456: Sales Overview

Fetching dashboard details... done
Found 3 referenced cards
Exporting card 123: Monthly Sales... done
Exporting card 124: Sales by Region... done
Exporting card 125: Top Products... done

Export complete!
Output directory: /tmp/metabase-20260205-183500/

Files created:
  - manifest.json
  - dashboard-456.json
  - card-123.json (Monthly Sales)
  - card-124.json (Sales by Region)
  - card-125.json (Top Products)
```

#### `metabase dashboards import`

Import a dashboard from a JSON definition file. Creates a new dashboard or updates an existing one.

**Options:**
- `--file <path>` - Path to manifest.json or dashboard JSON file (or use stdin)
- `--id <id>` - Dashboard ID to update (if omitted, creates new dashboard)
- `--collection-id <id>` - Target collection (overrides file)
- `--database-id <id>` - Target database for cards
- `--cards-only` - Only import/update cards, skip dashboard
- `--dashboard-only` - Only import/update dashboard, assume cards exist
- `--dry-run` - Show what would be imported without making changes
- `--json` - JSON output

**Examples:**
```bash
# Create new dashboard from manifest
metabase dashboards import --file /tmp/metabase-20260205-183500/manifest.json

# Update existing dashboard
metabase dashboards import --file /tmp/metabase-20260205-183500/manifest.json --id 789

# From stdin
cat dashboard-definition.json | metabase dashboards import --id 456
```

**Output (JSON only - no human-readable output needed):**
```json
{
  "success": true,
  "data": {
    "dashboard": {
      "id": 789,
      "name": "Sales Overview",
      "action": "created"
    },
    "cards": [
      {"id": 200, "name": "Monthly Sales", "action": "created"},
      {"id": 201, "name": "Sales by Region", "action": "created"}
    ]
  }
}
```

#### `metabase dashboards archive <id>`

Archive a dashboard (soft delete).

**Arguments:**
- `id` - Dashboard ID (required)

#### `metabase dashboards delete <id>`

Permanently delete a dashboard.

**Arguments:**
- `id` - Dashboard ID (required)

**Options:**
- `--force` - Skip confirmation

#### `metabase dashboards revisions <id>`

List dashboard revisions.

**Arguments:**
- `id` - Dashboard ID (required)

**Options:**
- `--json` - JSON output

#### `metabase dashboards revert <id> <revision_id>`

Revert dashboard to a previous revision.

**Arguments:**
- `id` - Dashboard ID (required)
- `revision_id` - Revision ID to revert to (required)

---

### `metabase search`

Global search across all Metabase entities.

```bash
metabase search <query>
```

**Arguments:**
- `query` - Search term (required)

**Options:**
- `--models <types>` - Filter by type: card, dashboard, collection, database, table, dataset, segment, metric, action
- `--collection-id <id>` - Search within collection
- `--database-id <id>` - Filter by database
- `--archived` - Search archived items
- `--created-by <user_id>` - Filter by creator
- `--limit <n>` - Max results (default: 50)
- `--json` - JSON output

**Example:**
```bash
metabase search "sales" --models card,dashboard
```

**Output (JSON):**
```json
{
  "success": true,
  "data": {
    "query": "sales",
    "total_results": 15,
    "results": [
      {
        "id": 123,
        "model": "card",
        "name": "Monthly Sales",
        "description": "Sales aggregated by month",
        "collection": {
          "id": 42,
          "name": "Sales Reports",
          "path": ["Analytics", "Sales Reports"]
        },
        "updated_at": "2026-02-01T14:30:00Z"
      },
      {
        "id": 456,
        "model": "dashboard",
        "name": "Sales Overview",
        "description": "Key sales metrics",
        "collection": {
          "id": 42,
          "name": "Sales Reports",
          "path": ["Analytics", "Sales Reports"]
        },
        "updated_at": "2026-02-05T12:00:00Z"
      }
    ]
  }
}
```

---

### `metabase resolve`

**Designed for LLM agents.** Parse a Metabase URL and return information about the referenced entity.

```bash
metabase resolve <url>
```

**Arguments:**
- `url` - Metabase URL (required). Can be full URL or path only.

**Options:**
- `--json` - JSON output

**Supported URL formats:**
- `https://metabase.example.com/question/123` - Card/question
- `https://metabase.example.com/dashboard/456` - Dashboard
- `https://metabase.example.com/collection/42` - Collection
- `/question/123` - Path only (uses configured instance)
- `/dashboard/456-sales-overview` - With slug

**Examples:**
```bash
metabase resolve "https://metabase.example.com/question/123"
metabase resolve "/dashboard/456"
```

**Output (human):**
```
URL: https://metabase.example.com/question/123

Entity Type: card
Entity ID: 123
Name: Monthly Sales
Description: Sales aggregated by month
Collection: Sales Reports (/Analytics/Sales Reports)
Database: Production (id: 1)
Last Updated: 2026-02-01T14:30:00Z
```

**Output (JSON):**
```json
{
  "success": true,
  "data": {
    "url": "https://metabase.example.com/question/123",
    "entity_type": "card",
    "entity_id": 123,
    "entity": {
      "id": 123,
      "name": "Monthly Sales",
      "description": "Sales aggregated by month",
      "collection_id": 42,
      "collection": {
        "id": 42,
        "name": "Sales Reports",
        "path": ["Analytics", "Sales Reports"]
      },
      "database_id": 1,
      "database_name": "Production",
      "display": "bar",
      "updated_at": "2026-02-01T14:30:00Z"
    }
  }
}
```

---

## File Output Convention

All export and run operations create files in a timestamped directory:

```
/tmp/metabase-<YYYYMMDD-HHMMSS>/
```

For example:
```
/tmp/metabase-20260205-183500/
```

This ensures:
- No file conflicts between export operations
- Easy cleanup of temporary files
- Clear association of files from the same export

### Export File Formats

All export files use a consistent structure:

```json
{
  "export_version": "1.0",
  "export_timestamp": "2026-02-05T18:35:00Z",
  "type": "card|dashboard",
  "source": {
    "instance_url": "https://metabase.example.com",
    "card_id": 123,        // or dashboard_id
    "database_id": 1       // original database
  },
  "card|dashboard": {
    // entity definition
  }
}
```

---

## LLM Agent Workflow Examples

### Example 1: Update a SQL query in a dashboard

```bash
# 1. Resolve URL to understand what we're working with
metabase resolve "https://metabase.example.com/dashboard/456" --json

# 2. Export the dashboard with all cards
metabase dashboards export 456 --json
# Returns: {"success": true, "data": {"output_dir": "/tmp/metabase-20260205-183500/", ...}}

# 3. Read and modify the card file (done by LLM)
# Edit /tmp/metabase-20260205-183500/card-123.json

# 4. Update the card
metabase cards import --file /tmp/metabase-20260205-183500/card-123.json --id 123 --json
```

### Example 2: Find and explore a collection

```bash
# 1. Search for collections using tree command
metabase collections tree --search "analytics" --levels 2 --json

# 2. List items in the found collection
metabase collections items 42 --models card,dashboard --json

# 3. Get details of a specific card
metabase cards get 123 --json
```

### Example 3: Run a card and get results

```bash
# 1. Run the card - outputs both JSON and CSV to /tmp
metabase cards run 123 --json
# Returns paths to both result files

# 2. Results are available at:
#    /tmp/metabase-20260205-183500/card-123-results.json
#    /tmp/metabase-20260205-183500/card-123-results.csv
```

### Example 4: Clone a dashboard to a new collection

```bash
# 1. Export the source dashboard
metabase dashboards export 456

# 2. Import to new collection (creates new dashboard and cards)
metabase dashboards import --file /tmp/metabase-20260205-183500/manifest.json \
  --collection-id 100 \
  --json
```

---

## Error Handling

All commands return a non-zero exit code on failure. With `--json`, errors are returned as:

```json
{
  "success": false,
  "error": {
    "code": "API_ERROR",
    "message": "Card with ID 123 not found",
    "details": {
      "status_code": 404,
      "api_response": {...}
    }
  }
}
```

Common error codes:
- `AUTH_ERROR` - Authentication failed
- `SESSION_EXPIRED` - Session expired (will auto-refresh if credentials available)
- `NOT_FOUND` - Entity not found
- `PERMISSION_DENIED` - Insufficient permissions
- `VALIDATION_ERROR` - Invalid input
- `API_ERROR` - Metabase API error
- `FILE_ERROR` - File read/write error

---

## Implementation Notes

### Typer Command Groups

```python
# cli.py
app = typer.Typer(name="metabase")

# Command groups
auth_app = typer.Typer(name="auth", help="Authentication commands")
databases_app = typer.Typer(name="databases", help="Database operations")
collections_app = typer.Typer(name="collections", help="Collection operations")
cards_app = typer.Typer(name="cards", help="Card/query operations")
dashboards_app = typer.Typer(name="dashboards", help="Dashboard operations")

app.add_typer(auth_app)
app.add_typer(databases_app)
app.add_typer(collections_app)
app.add_typer(cards_app)
app.add_typer(dashboards_app)

# Aliases for cards
app.add_typer(cards_app, name="queries")
app.add_typer(cards_app, name="questions")
```

### Session Management

```python
# auth.py
def get_session() -> str:
    """Get valid session, refreshing if needed."""
    config = load_config()

    if config.auth_method == "api_key":
        return config.api_key

    if config.session_id:
        if is_session_valid(config.session_id):
            return config.session_id

    # Session expired or missing - refresh if we have credentials
    if config.auth_method == "credentials" and config.username and config.password:
        new_session = authenticate(config.username, config.password)
        save_session_to_config(new_session)
        return new_session

    raise AuthError("Session expired. Please run 'metabase auth login'")
```

### Output Utilities

```python
# output.py
def output_result(data: dict, json_mode: bool = False) -> None:
    """Output data in appropriate format."""
    if json_mode:
        print(json.dumps({"success": True, "data": data}, indent=2))
    else:
        # Use Rich for formatted output
        console.print(format_for_humans(data))
```

### File Export Utilities

```python
# export.py
from datetime import datetime
from pathlib import Path

def get_export_dir() -> Path:
    """Create and return timestamped export directory."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dir_path = Path(f"/tmp/metabase-{timestamp}")
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path

def write_export_file(dir_path: Path, filename: str, data: dict) -> Path:
    """Write export file with standard envelope."""
    file_path = dir_path / filename
    export_data = {
        "export_version": "1.0",
        "export_timestamp": datetime.now().isoformat() + "Z",
        **data
    }
    file_path.write_text(json.dumps(export_data, indent=2))
    return file_path
```

---

## Summary

This CLI structure provides:

1. **Simplified command set** - Merged similar functionality (search+tree, run+export, create+update)
2. **LLM-optimized commands** like `collections tree --search` with context and `resolve` for URL parsing
3. **Consistent output** with `--json` flag for machine parsing
4. **File-based workflows** always using `/tmp/metabase-<timestamp>/` convention
5. **Smart session management** - Auto-refresh for credentials-based auth
6. **Context-rich responses** that minimize the need for multiple API calls

The design prioritizes the workflow of: **resolve URL -> export -> modify -> import** which is ideal for LLM-driven dashboard and query management.
