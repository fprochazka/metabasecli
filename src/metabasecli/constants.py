"""Shared constants used across the application.

This module contains configuration values and constants that are shared
across multiple modules in the Metabase CLI.
"""

__all__ = [
    "EXPORT_VERSION",
    "HTTP_TIMEOUT_SECONDS",
    "MODEL_CARD",
    "MODEL_DASHBOARD",
    "MODEL_COLLECTION",
    "MODEL_DATABASE",
    "MODEL_TABLE",
    "MODEL_DATASET",
    "MODEL_METRIC",
    "MODEL_SEGMENT",
    "MODEL_ACTION",
    "SEARCHABLE_MODELS",
]

# Export file format version
EXPORT_VERSION = "1.0"

# HTTP client configuration
HTTP_TIMEOUT_SECONDS = 60.0

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
