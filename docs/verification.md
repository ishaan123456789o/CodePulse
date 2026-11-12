# Verification record

Verified locally on November 12, 2026 using Python 3.13, Node 24, PostgreSQL 15.17, Redis 8.6 and Playwright Chromium. The Compose/CI targets use Python 3.13, Node 22, PostgreSQL 17 and Redis 7; that exact container combination requires a Docker host or CI run.

## Verified

- Backend: 24 tests pass with in-memory SQLite and with a real, isolated PostgreSQL database.
- Covered: coverage boundaries, negative growth, uneven timestamps, acceleration, deterministic scores, peer sample requirements, early/observed separation, immutable snapshots, immutable GitHub identity across renames, pagination/filter/search, idempotent watchlists, workspace partitioning, optional activity completeness, malformed external responses, retry limits, shared cooldown behavior, missing token, Redis failure, and stale-job recovery.
- Alembic: upgrade to head, downgrade to base, re-upgrade, and no-drift checks against PostgreSQL. SQLite migration round trip also passes; PostgreSQL-only expression indexes are intentionally absent there.
- Production frontend build succeeds with Next.js Webpack. Strict TypeScript, formatting, and two frontend utility tests pass.
- Four browser E2E workflows pass against the real API/PostgreSQL demo database: discovery/filtering/detail/chart/watchlist/reload/remove; overview/baseline/analytics/settings; mobile navigation and viewport containment; empty and error states. All fixture data is explicitly labeled synthetic.
- Real Redis and Celery worker delivery: discovery/tracking return `unconfigured` without a token; scoring and recovery complete; worker responds to ping; Celery Beat starts successfully.
- API readiness verifies PostgreSQL and Redis, and status/search/summary responses were exercised against running services.
- Desktop and 390px mobile screenshots visually inspected; mobile table overflow is contained in a keyboard-focusable scroll region.
- Compose YAML parsed and its seven-service structure, shared environment, persistence volumes, and migration dependencies inspected. Lockfiles reference public package registries.

## Not verified

- Live authenticated GitHub ingestion. No token was supplied; the user chose to continue without credentials. Network behaviors were tested with explicit mocks, not represented as successful live collection.
- Real multi-day collection. Synthetic observations exercise the analytics, but genuine 24h/7d/30d history can only accumulate over time after deployment.
- Full Docker image builds and `docker compose up`. No Docker engine is installed locally. A temporary standalone Compose binary was terminated by the host, so CLI configuration validation is also unverified. The repository includes a CI Compose smoke job; no remote CI run is claimed here.
- Deployment, TLS/proxy authentication, remote GitHub publication, sustained load testing, and backup/restore drills.

## Local preview

The local development database is separate from the demo database. The ignored `.env` uses the isolated local PostgreSQL port 55432 and Redis port 56379. The live-mode preview was started at http://localhost:3000, backed by the API on port 8000, with readiness confirmed and zero fixture repositories. The generated screenshots below are from **explicit demo mode**, with synthetic data, solely for UI verification:

- [Desktop overview](screenshots/demo-overview.png)
- [Mobile discovery](screenshots/demo-mobile.png)

The project source and logical commits are local unless a later user-authorized publication step is performed.

## CodePulse Forecast verification

Verified locally on November 12, 2026 after adding Forecast:

- 40 backend tests pass on SQLite and PostgreSQL, including forecast coverage, future-observation and insertion-time leakage, immutable daily predictions, day rollover, source isolation, delayed/missing outcomes, boundary tolerance, elapsed-time normalization, filters and pagination.
- Migration `0005_forecasts` upgrades, downgrades to `0004`, re-upgrades and passes Alembic no-drift checks on an isolated PostgreSQL database. SQLite migration is exercised by browser test setup.
- Six full browser workflows pass, including the new forecast table/filter, repository cards, insufficient-history state, mobile containment, empty and error states. The two Forecast workflows were rerun after UTC timestamp normalization.
- Frontend production build, TypeScript, two unit tests, formatting and backend lint pass. Desktop and mobile Forecast screenshots were visually inspected with explicitly synthetic data.
- Local live-mode preview migrated and restarted. `/forecast` returns HTTP 200; forecast APIs correctly return empty results, zero evaluated outcomes and null accuracy metrics. The operator forecast job completes with zero predictions when no history is available.
- Real seven-day predictive performance and a learned model remain unverified/unimplemented respectively. No synthetic outcome is presented as live model performance. See [forecast methodology](forecast.md) for the next modeling stage.
