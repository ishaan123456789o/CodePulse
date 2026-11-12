# CodePulse implementation

- [x] Phase 1 — foundation: monorepo, settings, database, migrations, containers
- [x] Phase 2 — GitHub client, discovery, enrichment, idempotent snapshots, scheduler
- [x] Phase 3 — coverage-aware analytics, deterministic scores, explainability, tests
- [x] Phase 4 — typed API, filtering, pagination, watchlist, health
- [x] Phase 5 — responsive live dashboard, discovery, details, analytics, settings
- [x] Phase 6 — API integration tests, browser tests, builds, CI
- [x] Phase 7 — deployment and operations documentation, final verification

## External dependencies
GitHub token for live ingestion; PostgreSQL and Redis for full integration. Tests use explicit mocked GitHub responses. No fixture data is loaded into production by default. Docker availability and live token access must be verified, never assumed.

## Final verification
- 24 backend tests pass on SQLite and PostgreSQL; 2 frontend unit tests and 4 real-API browser workflows pass.
- Frontend production build, TypeScript, formatting, migrations and PostgreSQL schema consistency pass.
- Real Redis/Celery smoke jobs pass without credentials.
- Docker runtime startup and authenticated GitHub ingestion remain externally unverified; see docs/verification.md.

## CodePulse Forecast — initial implementation
- [x] Versioned, coverage-aware seven-day damped-trend model and explicit breakout target.
- [x] Daily immutable predictions, hourly scheduling, delayed outcome evaluation and baseline comparison.
- [x] Migration, typed API, ranked Forecast page and repository cards.
- [x] Leakage, coverage, persistence, source isolation, API and browser tests.
- [ ] Gather genuine histories and prospective outcomes; assess predictive performance.
- [ ] Train and validate a learned model with purged chronological splits before promotion.
