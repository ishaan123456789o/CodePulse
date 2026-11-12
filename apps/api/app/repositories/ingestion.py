from datetime import datetime, timedelta
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.engine import utc
from app.github.discovery import classify
from app.github.schemas import GitHubRepository
from app.models.entities import Repository, Snapshot


def insert_for(session: AsyncSession, model):
    return pg_insert(model) if session.bind.dialect.name == "postgresql" else sqlite_insert(model)


def parse_date(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


async def upsert_repository(
    session: AsyncSession,
    data: dict[str, Any],
    now: datetime,
    category: str = "General Open Source",
    etag: str | None = None,
) -> tuple[Repository, bool]:
    try:
        data = GitHubRepository.model_validate(data).model_dump(mode="json")
    except ValidationError:
        raise ValueError("GitHub repository metadata is incomplete or invalid") from None
    if data.get("private") or data.get("visibility", "public") != "public":
        raise ValueError("Only public repositories can be tracked")
    existing = await session.scalar(select(Repository.id).where(Repository.github_id == data["id"]))
    topics = data.get("topics", [])
    values = dict(
        github_id=data["id"],
        owner=data["owner"]["login"],
        name=data["name"],
        full_name=data["full_name"],
        url="https://github.com/" + data["full_name"],
        description=data.get("description"),
        language=data.get("language"),
        topics=topics,
        category=classify(topics, category),
        created_at_github=parse_date(data["created_at"]),
        pushed_at=parse_date(data.get("pushed_at")),
        updated_at_github=parse_date(data.get("updated_at")),
        stars=data["stargazers_count"],
        forks=data["forks_count"],
        open_issues=data["open_issues_count"],
        default_branch=data.get("default_branch", "main"),
        license=(data.get("license") or {}).get("spdx_id"),
        size=data.get("size"),
        archived=data.get("archived", False),
        disabled=data.get("disabled", False),
        last_fetched_at=now,
        updated_at=now,
        etag=etag,
    )
    statement = insert_for(session, Repository).values(
        **values, discovered_at=now, created_at=now, next_fetch_at=now
    )
    statement = statement.on_conflict_do_update(
        index_elements=["github_id"], set_=values
    ).returning(Repository)
    repo = (await session.execute(statement.execution_options(populate_existing=True))).scalar_one()
    return repo, existing is None


async def record_snapshot(
    session: AsyncSession,
    repo: Repository,
    now: datetime,
    cadence: int,
    source: str = "github_rest",
) -> None:
    # Hourly UTC buckets remain stable when priority changes and across retries.
    bucket = now.replace(minute=0, second=0, microsecond=0)
    activity_fresh = repo.activity_fetched_at is not None and now - utc(
        repo.activity_fetched_at
    ) <= timedelta(hours=6)
    statement = (
        insert_for(session, Snapshot)
        .values(
            repository_id=repo.id,
            observed_at=now,
            observation_bucket=bucket,
            stars=repo.stars,
            forks=repo.forks,
            open_issues=repo.open_issues,
            pushed_at=repo.pushed_at,
            contributors=repo.contributors if activity_fresh else None,
            commits_7d=repo.commits_7d if activity_fresh else None,
            collection_source=source,
            created_at=now,
        )
        .on_conflict_do_nothing(index_elements=["repository_id", "observation_bucket"])
    )
    await session.execute(statement)
    repo.last_fetched_at = now
    repo.next_fetch_at = now + timedelta(hours=cadence)
