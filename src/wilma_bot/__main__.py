"""Entry point — run the MCP server over stdio."""

import logging

from wilma_bot.client import WilmaClient
from wilma_bot.config import settings
from wilma_bot.mcp.server import create_server

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

# Module-level server instance — required for `mcp dev` discovery.
_client = WilmaClient(
    base_url=settings.base_url,
    username=settings.username,
    password=settings.password,
    timeout=settings.session_timeout,
)
server = create_server(_client)


def main() -> None:
    server.run()


if __name__ == "__main__":
    main()
