FROM python:3.12-slim AS builder

WORKDIR /tmp

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

COPY pyproject.toml uv.lock ./

RUN uv export --no-dev --no-hashes -o requirements.txt \
 && uv build --no-dev

FROM python:3.12-slim

LABEL org.opencontainers.image.source=https://github.com/hugobatista/kleys
LABEL security.scan="true"
LABEL maintainer="Hugo Batista <code@hugobatista.com>"

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_ROOT_USER_ACTION=ignore

WORKDIR /app

COPY --from=builder /tmp/requirements.txt ./
RUN pip install --no-cache --upgrade pip \
 && pip install --no-cache --upgrade -r ./requirements.txt \
 && addgroup --system app && adduser --system --ingroup app app

COPY --from=builder /tmp/dist/*.whl /tmp/
RUN pip install --no-cache /tmp/*.whl && rm /tmp/*.whl

USER app

HEALTHCHECK --interval=300s --timeout=10s --start-period=5s --retries=3 \
    CMD kleys show --help || exit 1

ENTRYPOINT ["kleys"]
