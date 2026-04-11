"""Entry point — run the MCP server over stdio."""

import asyncio
import logging

from mcp.server.stdio import stdio_server

from wilma_bot.client import WilmaClient
from wilma_bot.config import settings
from wilma_bot.mcp.server import create_server, get_initialization_options

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


async def _run() -> None:
    client = WilmaClient(
        base_url=settings.base_url,
        username=settings.username,
        password=settings.password,
        timeout=settings.session_timeout,
    )
    server = create_server(client)
    init_opts = get_initialization_options(server)

    async with stdio_server() as (read_stream, write_stream):
        logger.info("Wilma Bot MCP server started")
        await server.run(read_stream, write_stream, init_opts)


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
