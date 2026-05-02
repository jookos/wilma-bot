"""Wilma mock server CLI entry point."""

import argparse

from wilma_bot.mock_server.server import app, configure_server


def main():
    parser = argparse.ArgumentParser(description="Wilma Mock Server")
    parser.add_argument("--config", default="mock-config.yaml", help="Path to config file")
    parser.add_argument("--port", type=int, default=9090, help="Port to listen on")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    args = parser.parse_args()

    print(f"Starting Wilma Mock Server on {args.host}:{args.port}")
    print(f"Loading config from {args.config}")

    configure_server(args.config)

    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
