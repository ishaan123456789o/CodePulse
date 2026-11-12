# CodePulse

**Which open-source projects are gaining unusual traction right now, and why?**

CodePulse discovers public GitHub repositories, collects immutable observations, and explains their momentum relative to their size and history. It is a working Next.js + FastAPI application with PostgreSQL, Redis, Celery workers and Beat.

No GitHub token is required to start the app. Without one, the index starts empty and Settings reports ingestion as **unconfigured**. Production pages never substitute fabricated repositories or historical growth. The explicitly labeled demo uses a separate database.

## Quick start

Requirements: Docker Engine/Desktop with Compose v2, Git, and Make.

```sh
git clone https://github.com/ishaan123456789o/CodePulse.git
cd CodePulse
make setup
# Optional: set GITHUB_TOKEN in the ignored .env file.
make up
```

Open **http://localhost:3000**. API documentation: **http://localhost:8000/docs**. Compose starts PostgreSQL, Redis, a migration job, API, worker, Beat, and the web server. Database and Redis data use named persistent volumes. `make down` keeps those volumes.

For live data, create a GitHub fine-grained personal access token that can read public repository metadata, put it in `.env` as `GITHUB_TOKEN`, and restart:

```sh
docker compose up -d --force-recreate api worker beat
make discover
make track
make score
```

Never commit the token. Repository write permissions, private repository access, and an LLM account are unnecessary. Optional commit enrichment may need Contents read permission, depending on token configuration; metadata collection continues if optional endpoints are inaccessible.

Discovery establishes candidates. Tracking establishes the first real baseline. **A genuine 24-hour metric requires at least 24 hours of real observations**; 7-day and 30-day metrics need correspondingly longer histories. Scoring runs hourly against the start of the current UTC hour, so new observations can take up to one hour to enter scores. The separate early-discovery heuristic is available sooner.

## Features

- Rotating discovery across ten categories, creation windows, star thresholds, topics and optional languages/custom search queries.
- Rename/transfer-safe identity through immutable GitHub IDs; PostgreSQL upserts and unique observation buckets.
- Configurable 1h / 6h / 24h tracking, per-run budgets, conditional requests, resource-specific quotas, shared cooldowns, and bounded retries.
- Pure, deterministic analytics with coverage checks, actual elapsed rates, comparable-window acceleration, peer percentiles, score history and factor contributions.
- Overview, measured Trending, Discover, repository analytics, persistent Watchlist, aggregate Analytics, and Settings pages.
- **CodePulse Forecast:** experimental seven-day net-star projections, potential-breakout ranking, saved daily predictions, and delayed outcome evaluation against a recent-rate baseline. Requires at least 14 days of observations; see [forecast methodology](docs/forecast.md).
- Search, category/language/star/score filters, server pagination and sorting; real star and fork charts; empty/loading/error states.
- Anonymous browser workspace watchlists. These are persistent identifiers, **not authentication**.
- Optional bounded commit/activity enrichment; deterministic explanations work without an LLM.
- OpenAPI schemas, structured logs, readiness checks, migration tooling, CI and browser workflow tests.

## Explicit demo mode

Use a **separate Compose project and database**. Stop the normal stack first if it occupies the same ports:

```sh
docker compose down
POSTGRES_DB=codepulse_demo DEMO_MODE=true docker compose -p codepulse-demo up --build -d
POSTGRES_DB=codepulse_demo DEMO_MODE=true docker compose -p codepulse-demo exec worker python -m app.workers.cli demo
```

Every page displays a demo banner; API collection responses include `demo: true`. Repositories are named `codepulse-demo/fixture-*`, descriptions identify them as synthetic, and snapshots have source `synthetic_demo_fixture`. Live GitHub collection is disabled in demo mode. Startup refuses demo mode unless the database name contains `demo`. Demo data is never automatically loaded into a normal database.

To return to live mode, stop the demo project and run `make up` with `DEMO_MODE=false` and the normal database name.

## Development without Docker

Requirements: Python 3.12+, uv, Node.js 22+, npm, a running PostgreSQL 15+ server and Redis 7+.

```sh
make setup
# Set DATABASE_URL and REDIS_URL in .env for your local services.
cd apps/api
uv sync --frozen
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In separate terminals:

```sh
cd apps/api
uv run celery -A app.workers.tasks:celery worker --loglevel=INFO --concurrency=1
# Another terminal, same directory:
uv run celery -A app.workers.tasks:celery beat --loglevel=INFO --schedule=/tmp/codepulse-beat
```

```sh
cd apps/web
npm ci
npm run dev
```

The frontend proxies `/api/v1/*` to `API_INTERNAL_URL` (default `http://localhost:8000`). If using a different API URL, set it in the frontend process environment. The Python process reads the root `.env`; Next.js does not read that parent file automatically. Production frontend: `npm run build && npm start`. The start script includes static assets in Next.js standalone output.

## Tests and checks

```sh
cd apps/api
uv run ruff check app tests alembic
uv run ruff format --check app tests alembic
uv run pytest
uv run alembic upgrade head
uv run alembic check
```

The default test database is in-memory SQLite, with mocked GitHub responses explicitly confined to tests. To verify PostgreSQL semantics, create a disposable database whose name contains `test`:

```sh
TEST_DATABASE_URL=postgresql+asyncpg://codepulse:password@localhost:5432/codepulse_test uv run pytest
```

**That test database is reset. Never point this command at valuable data.**

```sh
cd apps/web
npm ci
npm run test
npm run typecheck
npm run build
npx playwright install chromium
npm run test:e2e
```

Browser tests start a real API and built frontend and seed an isolated, explicitly labeled demo database. The default E2E database is a local SQLite file, usable through the API dev dependency `aiosqlite`; set `E2E_DATABASE_URL` to a separate PostgreSQL database containing `demo` for production-dialect coverage. Set `E2E_REDIS_URL` if Redis uses a nondefault port. Ports 8100 and 3100 must be free. CI runs PostgreSQL migrations, PostgreSQL API tests, frontend checks, browser workflows, and a separate full Docker Compose smoke job.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `GITHUB_TOKEN` | empty | Public repository access; absence disables live collection |
| `DATABASE_URL` | local PostgreSQL URL | Async SQLAlchemy database URL |
| `REDIS_URL` | `redis://localhost:6379/0` | Broker, lock, cooldown and cache storage |
| `DEMO_MODE` | `false` | Explicit, isolated synthetic fixture environment |
| `DISCOVERY_REQUEST_BUDGET` | `10` | Maximum HTTP attempts per discovery run |
| `TRACKING_REQUEST_BUDGET` | `60` | Maximum HTTP attempts per tracking run |
| `DISCOVERY_INTERVAL_SECONDS` | `21600` | Discovery every six hours |
| `TRACK_HIGH_HOURS` / `TRACK_NORMAL_HOURS` / `TRACK_LOW_HOURS` | `1` / `6` / `24` | Tracking cadences |
| `GITHUB_MIN_INTERVAL_SECONDS` | `2` | Minimum delay between serialized HTTP attempts |
| `DISCOVERY_LANGUAGES` | `[]` | JSON list; periodically rotates language constraints |
| `DISCOVERY_EXTRA_QUERIES` | `[]` | JSON list of additional GitHub search queries |
| `OPTIONAL_ACTIVITY_ENABLED` | `false` | Up to two extra requests for complete seven-day commit activity |
| `SUMMARY_CACHE_SECONDS` | `30` | Redis dashboard summary TTL; `0` disables |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Explicit allowed origins for direct API use |

Python configuration also accepts `DISCOVERY_TOPICS` as a JSON list. The default list spans all ten categories. Add an explicit Compose environment entry when overriding it in containers. Scoring weights live in `apps/api/app/analytics/engine.py`; bump `VERSION` when changing scoring semantics.

## API

All endpoints are under `/api/v1`: health/readiness, dashboard summary, repositories and their history/metrics/score, trending, discover, search, categories, languages, watchlist, system status, forecast rankings, repository forecasts, and forecast validation. See generated `/docs` for exact schemas.

List queries support `q`, `category`, `language`, `min_stars`, `max_stars`, `min_score`, `score_type`, `new_only`, `emerging`, `time_window`, `sort`, `page`, and `page_size`. Trending includes only fresh **observed momentum** scores. Other views clearly label both score types; score sorting groups observed momentum ahead of early heuristics because their scores are not statistically interchangeable. Search covers the stored CodePulse index, not a synchronous GitHub search.

Watchlist mutations and reads require `X-Workspace-Id: <UUID>`. The browser creates and persists this ID locally. There is no public ingestion-trigger endpoint. Operators use `python -m app.workers.cli discover|track|score|recover` or Make targets.

## Scope and operational limits

- Discovery is a rotating, budgeted sample, not complete coverage of GitHub.
- Momentum scores explain observed growth. The separate Forecast feature is an experimental statistical projection; it is not a trained machine-learning model and live predictive performance is unverified.
- Current scores are calculated hourly; old scores carry a stale flag. Summaries may lag by the cache TTL.
- Optional activity counts only the default branch’s last seven days, and requires a complete result within 200 commits. Partial or inaccessible activity is unavailable; last successfully collected metadata carries a separate timestamp.
- The reference deployment is a trusted personal workspace. Add authentication and workspace authorization before a public multi-user deployment. Anonymous IDs alone do not provide account security.
- Use one Beat instance. Collectors serialize through a shared Redis lock. The worker default concurrency is one.
- Scoring currently loads up to 63 days of snapshots for the tracked cohort into memory. For large deployments, batch this work and define retention/partitioning policies before scaling beyond a personal index.
- An LLM provider protocol exists as an extension boundary; no LLM integration or API key is required or enabled.

See [architecture](docs/architecture.md), [analytics methodology](docs/analytics.md), [deployment and recovery](docs/deployment.md), and [verification record](docs/verification.md).
