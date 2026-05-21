FROM python:3.12-slim AS builder

WORKDIR /tmp

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

COPY pyproject.toml uv.lock README.md ./
COPY src src/

RUN uv export --no-dev --no-hashes --no-emit-project -o requirements.txt \
 && uv build

FROM python:3.12-slim

LABEL org.opencontainers.image.source=https://github.com/hugobatista/kleys
LABEL security.scan="true"
LABEL maintainer="Hugo Batista <code@hugobatista.com>"

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_ROOT_USER_ACTION=ignore \
    XDG_DATA_HOME=/app/data

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-dbus \
    python3-secretstorage \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /tmp/requirements.txt ./
RUN pip install --no-cache --upgrade pip \
 && pip install --no-cache --upgrade -r ./requirements.txt keyrings.alt \
 && addgroup --system app && adduser --system --ingroup app app

COPY --from=builder /tmp/dist/*.whl /tmp/
RUN pip install --no-cache /tmp/*.whl && rm /tmp/*.whl \
 && mkdir -p /app/data && chown -R app:app /app/data

USER app

HEALTHCHECK --interval=300s --timeout=10s --start-period=5s --retries=3 \
    CMD kleys --help || exit 1

ENTRYPOINT ["kleys"]
