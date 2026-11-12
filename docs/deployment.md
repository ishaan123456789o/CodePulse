# Deployment and operations

## Single-host deployment

Run the Compose stack on a trusted host with durable storage, at least 2 CPU cores and 4 GB memory for a small index. Build/pin reviewed images in your registry for repeatable releases. The checked-in image tags pin major versions; lockfiles pin application dependencies. Put the web service behind a TLS reverse proxy and access control before exposing it publicly. Only the frontend needs to be public; keep PostgreSQL, Redis and the API on private interfaces. Compose binds published ports to loopback by default.

The application does not provide authenticated multi-user authorization. Browser workspace UUIDs partition watchlists, but anyone who knows an ID can use it. Protect the entire personal deployment with your reverse proxy's authentication. Proper future authentication must derive workspace ownership server-side, not trust a browser-provided ID.

Set a unique PostgreSQL password and inject secrets from the deployment secret manager. The example password is local-development-only. Do not include `.env` in build contexts or images. Rotate GitHub tokens through environment changes and restart API/worker/Beat. Never put tokens in `NEXT_PUBLIC_*` variables. Limit fine-grained GitHub permissions to public read access.

Run `alembic upgrade head` once before rolling out API/workers. Compose's migration dependency performs this automatically. Keep one Beat instance and at least one worker. Default `--concurrency=1` and a shared collector lock avoid concurrent GitHub collection. Workers have 3200s soft and 3300s hard limits, below the 3500s lock lease. The scheduler drops obsolete duplicate queue messages with expirations.

## Monitoring

- Liveness: `GET /api/v1/health`.
- Readiness: `GET /api/v1/health/ready`, requiring PostgreSQL and Redis.
- Settings / `/api/v1/system/status`: worker heartbeat, actual GitHub quota headers per resource, cooldown, latest discovery run, recent failures, budgets/cadences.
- JSON API request logs include request ID, method, path, status and duration. Request bodies, authorization headers and tokens are not logged.
- `docker compose logs -f api worker beat` for failures. Forward these to your preferred log service; alert on readiness failures, missing worker heartbeat >15m, rising failed jobs, repeated auth failures and stale observations.
- Worker commands return explicit `unconfigured` or `demo` status if live collection is disabled.

A healthy worker is not evidence of successful live GitHub collection. Inspect discovery results and observation timestamps. Search has a separate quota. Primary exhaustion waits until the response reset time; secondary limits wait at least 60 seconds and respect Retry-After, with jitter and a shared cooldown. No long rate-limit sleeps or infinite retries occupy workers. Failed network/5xx requests retry at most three attempts and still consume the per-run budget. 404/410 tracking failures defer for 24 hours. Rate limits and failures remain visible in jobs.

The optional 30s Redis summary cache is expendable. PostgreSQL is the source of truth. Watchlist responses are not shared-cached. If Redis is unavailable, read APIs continue without cache, but readiness degrades and scheduled collection needs recovery.

## Backup and restore

```sh
docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > codepulse.dump
# Restore into a deliberately selected, empty target database:
# pg_restore --dbname=<target-url> codepulse.dump
```

Store backups outside the host and test restores. Named volume `postgres_data` holds PostgreSQL data. Redis uses append-only persistence in `redis_data`. `docker compose down` preserves volumes; deleting volumes destroys data. PostgreSQL backups include watchlists and score history. Redis is recoverable coordination state, but clearing it resets discovery rotation and cached rate limits; wait out GitHub limits before restarting collectors.

## Failure recovery

1. Restore database/Redis connectivity and confirm readiness.
2. Restart worker and Beat; do not launch a second Beat.
3. Stale running jobs older than two hours are marked interrupted by the hourly recovery task (or `make recover`). Repository due timestamps remain authoritative and subsequent tracking retries due work.
4. Retry discovery or tracking through operator CLI if necessary. Repository and observation upserts are retry-safe.
5. Run scoring after recovery. Missing observation periods remain gaps; the system never backfills fictional counts.

Optional activity remains null when inaccessible or incomplete. Default-branch commits are not a measure of all repository work. Disable optional activity first when quotas are tight. For thousands of rapidly changing repositories, tune discovery breadth, tracking budgets, batch scoring and snapshot retention. Do not increase concurrency or scrape HTML to circumvent GitHub limits.

## GitHub documentation consulted

- https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api
- https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api

Consulted November 12, 2026. Client uses REST API version `2026-03-10`, reports quotas from response headers, and does not assume all resource families share the same limit.
