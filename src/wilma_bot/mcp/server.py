"""MCP server wiring."""

from __future__ import annotations

import logging

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import ServerCapabilities, Tool, ToolsCapability

from wilma_bot.client import WilmaClient
from wilma_bot.mcp import tools as tool_handlers

logger = logging.getLogger(__name__)


def create_server(client: WilmaClient) -> Server:
    """Instantiate and configure the MCP server."""
    server: Server = Server("wilma-bot")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return tool_handlers.TOOLS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> object:  # type: ignore[type-arg]
        handler = tool_handlers.REGISTRY.get(name)
        if handler is None:
            raise ValueError(f"Unknown tool: {name!r}")
        return await handler(client, arguments)

    return server


def get_initialization_options(server: Server) -> InitializationOptions:
    return InitializationOptions(
        server_name="wilma-bot",
        server_version="0.1.0",
        capabilities=ServerCapabilities(tools=ToolsCapability(listChanged=False)),
    )
