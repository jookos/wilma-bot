IMAGE ?= jookos.org/wilma-bot
TAG ?= latest
PORT ?= 6060
MOCK_PORT ?= 9090

.PHONY: install test lint typecheck dev run image run-image inspector run-http run-mock

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

run-http:
	uv run wilma-bot --http $(PORT)

run-http-mock:
	WILMA_ENV_FILE=.env-mock uv run wilma-bot --http $(PORT)

run-mock:
	uv run python -m wilma_bot.mock_server --port $(MOCK_PORT)


image:
	docker build -t $(IMAGE):$(TAG) .

run-image:
	docker run -p $(PORT):$(PORT) --env-file .env $(IMAGE):$(TAG) --http $(PORT)

inspector:
	npx @modelcontextprotocol/inspector --remote-url http://localhost:$(PORT)/mcp
