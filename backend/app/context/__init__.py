"""
Data Context Module.

Provides credentials management for generated applications.
"""

from .data_context import (
    DataContext,
    get_keboola_credentials,
    inject_credentials_to_env,
    get_credentials_for_sandbox,
)

__all__ = [
    "DataContext",
    "get_keboola_credentials",
    "inject_credentials_to_env",
    "get_credentials_for_sandbox",
]
