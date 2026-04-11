IMAGE ?= jookos.org/wilma-bot
TAG ?= latest
PORT ?= 6060

.PHONY: install test lint typecheck dev run docker-build

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

image:
	docker build -t $(IMAGE):$(TAG) .

run-image:
	docker run -p $(PORT):$(PORT) --env-file .env wilma-bot --http $(PORT)

inspector:
	npx @modelcontextprotocol/inspector
