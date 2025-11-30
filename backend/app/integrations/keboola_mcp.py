"""
Keboola MCP Server Integration.

Provides configuration for connecting to Keboola MCP server via stdio transport.
The MCP server enables data exploration during the design phase of app building.

Usage:
    The Keboola MCP server is integrated into the Claude Agent SDK as an external
    stdio MCP server. It provides tools for:
    - Exploring storage buckets and tables
    - Getting table schemas
    - Running SQL queries for data exploration
    - Searching for data assets

Environment Variables Required:
    KBC_STORAGE_API_URL: Keboola connection URL (e.g., https://connection.keboola.com)
    KBC_TOKEN: Keboola Storage API token (or KBC_STORAGE_TOKEN)

See: https://github.com/keboola/keboola-mcp-server
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# KEBOOLA MCP TOOLS - List of available tools for allowed_tools configuration
# =============================================================================

# Core exploration tools that the agent should use
KEBOOLA_MCP_TOOLS = [
    # Project & Storage exploration
    "mcp__keboola__get_project_info",
    "mcp__keboola__list_buckets",
    "mcp__keboola__list_tables",
    "mcp__keboola__get_table",
    "mcp__keboola__search",

    # Data querying
    "mcp__keboola__query_data",

    # Components & Jobs (optional, for advanced use)
    "mcp__keboola__list_components",
    "mcp__keboola__get_component",
    "mcp__keboola__list_component_configs",
    "mcp__keboola__get_component_config",
    "mcp__keboola__list_jobs",
    "mcp__keboola__get_job",

    # Transformations
    "mcp__keboola__list_transformations",
    "mcp__keboola__get_transformation",

    # Flows
    "mcp__keboola__list_flows",
    "mcp__keboola__get_flow",

    # Documentation
    "mcp__keboola__docs_search",
    "mcp__keboola__docs_retrieve",

    # SQL assistance
    "mcp__keboola__create_sql",
]


def get_keboola_mcp_config() -> dict[str, Any] | None:
    """
    Get Keboola MCP server configuration for Claude Agent SDK.

    Returns stdio transport configuration that spawns the keboola_mcp_server
    as a subprocess.

    Returns:
        dict: MCP server configuration for ClaudeAgentOptions.mcp_servers
        None: If Keboola credentials are not configured

    Example:
        config = get_keboola_mcp_config()
        if config:
            options = ClaudeAgentOptions(
                mcp_servers={"keboola": config},
                allowed_tools=[...] + KEBOOLA_MCP_TOOLS
            )
    """
    # Get Keboola credentials from environment
    # Support both KBC_STORAGE_API_URL and KBC_URL patterns
    storage_url = os.getenv("KBC_STORAGE_API_URL") or os.getenv("KBC_URL", "").rstrip("/")
    storage_token = os.getenv("KBC_STORAGE_TOKEN") or os.getenv("KBC_TOKEN")

    # Normalize URL - ensure it's the storage API URL format
    if storage_url:
        # Convert connection URL to proper format
        # e.g., "https://connection.keboola.com/" -> "https://connection.keboola.com"
        storage_url = storage_url.rstrip("/")

        # Log which URL we're using (without exposing token)
        logger.info(f"Keboola MCP configured with URL: {storage_url}")

    if not storage_url or not storage_token:
        logger.warning(
            "Keboola MCP not configured. Set KBC_STORAGE_API_URL and KBC_STORAGE_TOKEN "
            "(or KBC_URL and KBC_TOKEN) environment variables."
        )
        return None

    # Return stdio transport configuration
    # This will spawn keboola_mcp_server as a subprocess
    return {
        "type": "stdio",
        "command": "uvx",
        "args": ["keboola_mcp_server", "--transport", "stdio"],
        "env": {
            "KBC_STORAGE_API_URL": storage_url,
            "KBC_STORAGE_TOKEN": storage_token,
        }
    }


def get_essential_keboola_tools() -> list[str]:
    """
    Get the essential Keboola MCP tools for data exploration.

    Returns a minimal set of tools needed for basic data exploration
    during the design phase.

    Returns:
        list[str]: List of tool names for allowed_tools configuration
    """
    return [
        "mcp__keboola__get_project_info",
        "mcp__keboola__list_buckets",
        "mcp__keboola__list_tables",
        "mcp__keboola__get_table",
        "mcp__keboola__query_data",
        "mcp__keboola__search",
    ]


def is_keboola_configured() -> bool:
    """
    Check if Keboola credentials are configured.

    Returns:
        bool: True if Keboola environment variables are set
    """
    storage_url = os.getenv("KBC_STORAGE_API_URL") or os.getenv("KBC_URL")
    storage_token = os.getenv("KBC_STORAGE_TOKEN") or os.getenv("KBC_TOKEN")
    return bool(storage_url and storage_token)
