from datetime import timedelta

from sqlalchemy import select, update

from app.core.config import Settings
from app.github.client import BudgetExhausted, GitHubClient, GitHubError, RateLimited
from app.github.discovery import discovery_queries
from app.github.enrichment import enrich_activity
from app.models.entities import DiscoveryRun, IngestionJob, Repository, utcnow
from app.repositories.ingestion import record_snapshot, upsert_repository


def cadence(repo: Repository, settings: Settings) -> int:
    return {
        "high": settings.track_high_hours,
        "normal": settings.track_normal_hours,
        "low": settings.track_low_hours,
    }.get(repo.tracking_priority, settings.track_normal_hours)


async def discover(session_factory, client: GitHubClient, settings: Settings, rotation: int) -> int:
    count = 0
    queries = discovery_queries(utcnow(), rotation, settings.discovery_topics)
    if settings.discovery_languages and rotation % 3 == 2:
        language = settings.discovery_languages[rotation % len(settings.discovery_languages)]
        queries = [(q + f" language:{language}", category) for q, category in queries]
    if settings.discovery_extra_queries:
        queries.insert(
            0,
            (
                settings.discovery_extra_queries[rotation % len(settings.discovery_extra_queries)],
                "General Open Source",
            ),
        )
    for query, category in queries:
        if client.remaining <= 0:
            break
        async with session_factory() as session:
            run = DiscoveryRun(query=query)
            session.add(run)
            await session.commit()
            try:
                for page in range(1, 3):
                    result = await client.get(
                        "/search/repositories",
                        params={
                            "q": query,
                            "sort": "updated" if rotation % 2 else "stars",
                            "order": "desc",
                            "per_page": 30,
                            "page": page,
                        },
                    )
                    if not isinstance(result.data, dict) or not isinstance(
                        result.data.get("items"), list
                    ):
                        raise GitHubError("GitHub search returned an invalid response shape")
                    items = result.data["items"]
                    for item in items:
                        if item.get("private"):
                            continue
                        repo, inserted = await upsert_repository(session, item, utcnow(), category)
                        # Search is discovery only. Metadata observation is scheduled separately.
                        run.repositories_found += 1
                        run.repositories_inserted += int(inserted)
                        count += int(inserted)
                    await session.commit()
                    if not result.has_next or not items or client.remaining <= 0:
                        break
                run.status = "completed"
            except (GitHubError, ValueError) as exc:
                run.status = (
                    "deferred" if isinstance(exc, (RateLimited, BudgetExhausted)) else "failed"
                )
                run.error_message = str(exc)[:500]
                if isinstance(exc, RateLimited) or getattr(exc, "status", None) == 401:
                    run.completed_at = utcnow()
                    await session.commit()
                    break
            run.completed_at = utcnow()
            await session.commit()
    return count


async def track(session_factory, client: GitHubClient, settings: Settings) -> int:
    async with session_factory() as session:
        ids = (
            await session.scalars(
                select(Repository.id)
                .where(Repository.next_fetch_at <= utcnow(), Repository.disabled.is_(False))
                .order_by(Repository.next_fetch_at, Repository.id)
                .limit(settings.tracking_request_budget)
            )
        ).all()
    completed = 0
    for repo_id in ids:
        if client.remaining <= 0:
            break
        async with session_factory() as session:
            repo = await session.get(Repository, repo_id)
            job = IngestionJob(job_type="snapshot", repository_id=repo_id)
            session.add(job)
            await session.commit()
            try:
                result = await client.get(f"/repositories/{repo.github_id}", etag=repo.etag)
                if not result.not_modified:
                    repo, _ = await upsert_repository(
                        session, result.data, utcnow(), repo.category, result.etag
                    )
                if settings.optional_activity_enabled:
                    await enrich_activity(client, repo)
                await record_snapshot(session, repo, utcnow(), cadence(repo, settings))
                job.status = "completed"
                completed += 1
            except (GitHubError, ValueError) as exc:
                job.status = (
                    "deferred" if isinstance(exc, (RateLimited, BudgetExhausted)) else "failed"
                )
                job.error_message = str(exc)[:500]
                delay = (
                    timedelta(seconds=exc.delay)
                    if isinstance(exc, RateLimited)
                    else timedelta(hours=24 if getattr(exc, "status", None) in (404, 410) else 1)
                )
                repo.next_fetch_at = utcnow() + delay
                job.completed_at = utcnow()
                await session.commit()
                if (
                    isinstance(exc, (RateLimited, BudgetExhausted))
                    or getattr(exc, "status", None) == 401
                ):
                    break
            job.completed_at = utcnow()
            await session.commit()
    return completed


async def recover_jobs(session_factory) -> None:
    async with session_factory() as session:
        cutoff = utcnow() - timedelta(hours=2)
        for model, start in [
            (IngestionJob, IngestionJob.started_at),
            (DiscoveryRun, DiscoveryRun.started_at),
        ]:
            await session.execute(
                update(model)
                .where(model.status == "running", start < cutoff)
                .values(
                    status="interrupted",
                    completed_at=utcnow(),
                    error_message="Worker interrupted; due repositories will be retried by the scheduler",
                )
            )
        await session.commit()
