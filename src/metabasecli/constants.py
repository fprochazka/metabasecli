"""Shared constants used across the application."""

# Export file format version
EXPORT_VERSION = "1.0"

# HTTP client configuration
HTTP_TIMEOUT_SECONDS = 30.0

# Search result model types (as returned by Metabase API)
MODEL_CARD = "card"
MODEL_DASHBOARD = "dashboard"
MODEL_COLLECTION = "collection"
MODEL_DATABASE = "database"
MODEL_TABLE = "table"
MODEL_DATASET = "dataset"
MODEL_METRIC = "metric"
MODEL_SEGMENT = "segment"
MODEL_ACTION = "action"

# All searchable model types in display order
SEARCHABLE_MODELS = [
    MODEL_DASHBOARD,
    MODEL_CARD,
    MODEL_COLLECTION,
    MODEL_TABLE,
    MODEL_DATABASE,
    MODEL_DATASET,
    MODEL_METRIC,
    MODEL_SEGMENT,
    MODEL_ACTION,
]
