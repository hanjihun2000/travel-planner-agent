"""Register MCP toolsets used by the travel planner agent."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

LOGGER = logging.getLogger(__name__)


AVAILABLE_MCP_TOOLSETS: list[MCPToolset] = []


def _collect_postgres_env() -> dict[str, str] | None:
    """Gather environment variables required for the Postgres MCP server."""

    db_url = os.getenv("PAYMENTS_DB_URL")
    if not db_url:
        LOGGER.info(
            "Skipping Postgres MCP toolset registration because PAYMENTS_DB_URL is unset."
        )
        return None

    env: dict[str, str] = {"PAYMENTS_DB_URL": db_url}
    for key in (
        "PAYMENTS_DB_POOL_MIN",
        "PAYMENTS_DB_POOL_MAX",
        "PAYMENTS_DB_STATEMENT_TIMEOUT_MS",
        "PAYMENTS_MCP_LOG_LEVEL",
    ):
        value = os.getenv(key)
        if value:
            env[key] = value
    return env


def _register_postgres_toolset() -> MCPToolset | None:
    """Register the Postgres payments MCP toolset if configuration is present."""

    module_path = (
        Path(__file__).resolve().parent.parent
        / "mcp_servers"
        / "postgres_payments"
        / "server.py"
    )
    if not module_path.exists():
        LOGGER.warning("Postgres MCP server not found at %s", module_path)
        return None

    env = _collect_postgres_env()
    if env is None:
        return None

    module_name = "travel_planner_agent.mcp_servers.postgres_payments.server"

    toolset = MCPToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=sys.executable,
                args=["-m", module_name],
                env=env,
            )
        )
    )
    LOGGER.info("Registered Postgres payments MCP toolset via module %s", module_name)
    return toolset


toolset = _register_postgres_toolset()
if toolset is not None:
    AVAILABLE_MCP_TOOLSETS.append(toolset)


def _register_itinerary_export_toolset() -> MCPToolset | None:
    module_path = (
        Path(__file__).resolve().parent.parent
        / "mcp_servers"
        / "itinerary_export"
        / "server.py"
    )
    if not module_path.exists():
        LOGGER.warning("Itinerary export MCP server not found at %s", module_path)
        return None

    module_name = "travel_planner_agent.mcp_servers.itinerary_export.server"
    toolset = MCPToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=sys.executable,
                args=["-m", module_name],
            )
        )
    )
    LOGGER.info("Registered itinerary export MCP toolset via module %s", module_name)
    return toolset


export_toolset = _register_itinerary_export_toolset()
if export_toolset is not None:
    AVAILABLE_MCP_TOOLSETS.append(export_toolset)
