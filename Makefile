.PHONY: install test lint typecheck dev run

install:
	uv pip install -e ".[dev]"

test:
	uv run pytest

lint:
	uv run ruff check src tests
	uv run ruff format --check src tests

typecheck:
	uv run mypy src

dev:
	WILMA_USERNAME=$(WILMA_USERNAME) WILMA_PASSWORD=$(WILMA_PASSWORD) \
		uv run mcp dev src/wilma_bot/__main__.py

run:
	uv run wilma-bot
