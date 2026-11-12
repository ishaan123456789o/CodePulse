from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import func, select

from app.analytics.engine import Observation, measure, peer_group, utc
from app.core.config import get_settings
from app.models.entities import Repository, Snapshot, WatchlistEntry, utcnow
from app.repositories.catalog import get_repository, latest_scores, list_repositories
from app.repositories.ingestion import insert_for
from app.schemas.api import Filters, HistoryOut, MetricsOut, SnapshotOut, SummaryOut


async def require_repository(session, repo_id, window="24h", workspace=None):
    repo = await get_repository(session, repo_id, window, workspace)
    if repo is None:
        raise HTTPException(404, "Repository not found in the CodePulse index")
    return repo


async def history(session, repo_id, window):
    await require_repository(session, repo_id)
    query = select(Snapshot).where(Snapshot.repository_id == repo_id)
    if window != "all":
        query = query.where(
            Snapshot.observed_at
            >= utcnow() - timedelta(days={"24h": 1, "7d": 7, "30d": 30}[window])
        )
    points = (await session.scalars(query.order_by(Snapshot.observed_at))).all()
    return HistoryOut(
        repository_id=repo_id,
        time_window=window,
        observations=[SnapshotOut.model_validate(p) for p in points],
        demo=get_settings().demo_mode,
    )


async def metrics(session, repo_id, window):
    repo = await require_repository(session, repo_id, window)
    points = (
        await session.scalars(
            select(Snapshot)
            .where(
                Snapshot.repository_id == repo_id,
                Snapshot.observed_at >= utcnow() - timedelta(days=63),
            )
            .order_by(Snapshot.observed_at)
        )
    ).all()
    measurement = measure(
        [
            Observation(p.observed_at, p.stars, p.forks, p.contributors, p.commits_7d)
            for p in points
        ],
        window,
        utcnow(),
    )
    # Comparisons require at least ten measured peers in the same size/age group.
    group = peer_group(repo.stars, (utcnow() - utc(repo.created_at_github)).days)
    ranges = [(0, 99), (100, 999), (1000, 9999), (10000, None)]
    lower, upper = ranges[group[0]]
    candidates = await list_repositories(
        session,
        Filters(
            time_window=window,
            min_stars=lower,
            max_stars=upper,
            score_type="observed_momentum",
            page_size=100,
        ),
    )
    peers = [
        p
        for p in candidates.items
        if p.id != repo_id
        and peer_group(p.stars, (utcnow() - utc(p.created_at_github)).days) == group
    ]
    return MetricsOut(
        repository_id=repo_id,
        time_window=window,
        **measurement,
        peers=peers[:5] if len(peers) >= 10 else [],
    )


async def add_watchlist(session, workspace, repo_id):
    await require_repository(session, repo_id)
    statement = (
        insert_for(session, WatchlistEntry)
        .values(workspace_id=workspace, repository_id=repo_id)
        .on_conflict_do_nothing(index_elements=["workspace_id", "repository_id"])
    )
    await session.execute(statement)
    await session.commit()


async def remove_watchlist(session, workspace, repo_id):
    from sqlalchemy import delete

    await session.execute(
        delete(WatchlistEntry).where(
            WatchlistEntry.workspace_id == workspace, WatchlistEntry.repository_id == repo_id
        )
    )
    await session.commit()


async def summary(session, window):
    now = utcnow()
    score, ranked = latest_scores(window)
    measured = select(score).where(
        ranked.c.rn == 1,
        score.score_type == "observed_momentum",
        score.calculated_at >= now - timedelta(hours=2),
    )
    scores = (await session.scalars(measured)).all()
    counts = (
        await session.execute(
            select(Repository.category, func.count())
            .group_by(Repository.category)
            .order_by(func.count().desc())
        )
    ).all()
    return SummaryOut(
        repositories_tracked=await session.scalar(select(func.count(Repository.id))),
        emerging_repositories=await session.scalar(
            select(func.count(Repository.id)).where(
                Repository.stars < 10000,
                Repository.archived.is_(False),
                Repository.disabled.is_(False),
            )
        ),
        high_momentum_repositories=sum(s.score >= 65 for s in scores),
        new_discoveries_today=await session.scalar(
            select(func.count(Repository.id)).where(
                Repository.discovered_at >= now.replace(hour=0, minute=0, second=0, microsecond=0)
            )
        ),
        last_observation_at=await session.scalar(select(func.max(Snapshot.observed_at))),
        categories=[{"name": category, "count": count} for category, count in counts],
        momentum_distribution=[
            {"range": label, "count": sum(low <= s.score < high for s in scores)}
            for low, high, label in [
                (0, 20, "0–19"),
                (20, 40, "20–39"),
                (40, 60, "40–59"),
                (60, 80, "60–79"),
                (80, 101, "80–100"),
            ]
        ],
        fastest_growing=(
            await list_repositories(
                session,
                Filters(
                    time_window=window, sort="growth", score_type="observed_momentum", page_size=5
                ),
            )
        ).items,
        recently_discovered=(
            await list_repositories(
                session, Filters(time_window=window, sort="newest", page_size=5)
            )
        ).items,
        demo=get_settings().demo_mode,
    )
