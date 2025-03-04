"""
Configuration for InverseBias application.

This module exposes the configuration settings from the settings module.
"""

# Import and expose from settings module
from inversebias.config.settings import (
    settings,
    SOURCE_TO_URL,
    SUBJECTS,
    BIAS_THRESHOLD,
    NEWS_SOURCES,
)

# Define what's exported from this package
__all__ = [
    "settings",
    "SOURCE_TO_URL",
    "SUBJECTS",
    "BIAS_THRESHOLD",
    "NEWS_SOURCES",
]
