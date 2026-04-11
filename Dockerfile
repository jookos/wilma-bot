FROM python:3.12-alpine AS builder

WORKDIR /build

# Install build dependencies
RUN apk add --no-cache gcc musl-dev

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml README.md ./
COPY src/ src/

# Install the project and its dependencies into a virtual env
RUN uv venv /opt/venv && \
    uv pip install --python /opt/venv/bin/python --no-cache .


FROM python:3.12-alpine AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Non-root user for security
RUN adduser -D -u 1000 wilma

COPY --from=builder /opt/venv /opt/venv

USER wilma

ENTRYPOINT ["wilma-bot"]
