FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.9.30 /uv /usr/local/bin/uv
WORKDIR /app
COPY apps/api/pyproject.toml apps/api/uv.lock ./
RUN uv sync --frozen --no-dev
COPY apps/api/app ./app
RUN useradd -m -u 10001 codepulse && chown -R codepulse:codepulse /app
USER codepulse
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
CMD ["celery", "-A", "app.workers.tasks:celery", "worker", "--loglevel=INFO", "--concurrency=1"]
