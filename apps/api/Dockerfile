FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.9.30 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
RUN useradd -m -u 10001 codepulse && chown -R codepulse:codepulse /app
USER codepulse
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
