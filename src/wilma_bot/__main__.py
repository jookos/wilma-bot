"""Entry point — run the MCP server over stdio or HTTP (streamable-http)."""

import argparse
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
    parser = argparse.ArgumentParser(description="Wilma MCP server")
    parser.add_argument(
        "--http",
        metavar="PORT",
        type=int,
        default=None,
        help="Start as a streamable-HTTP MCP server on the given port (default: stdio)",
    )
    args = parser.parse_args()

    if args.http is not None:
        server.settings.port = args.http
        server.settings.host = "0.0.0.0"
        server.run(transport="streamable-http")
    else:
        server.run()


if __name__ == "__main__":
    main()
