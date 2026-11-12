from collections import defaultdict
from datetime import timedelta

from sqlalchemy import select

from app.analytics.engine import (
    WINDOW_DAYS,
    Observation,
    compute_early_discovery_score,
    compute_momentum_score,
    compute_peer_percentile,
    measure,
    peer_group,
    utc,
)
from app.models.entities import Repository, Score, Snapshot, utcnow
from app.repositories.ingestion import insert_for


async def score_all(session_factory) -> int:
    now = utcnow().replace(minute=0, second=0, microsecond=0)
    # Same hour => deterministic, idempotent scoring run. Observe only timestamps <= calculation.
    async with session_factory() as session:
        repos = (await session.scalars(select(Repository).order_by(Repository.id))).all()
        snapshots = (
            await session.scalars(
                select(Snapshot)
                .where(
                    Snapshot.observed_at >= now - timedelta(days=63), Snapshot.observed_at <= now
                )
                .order_by(Snapshot.observed_at)
            )
        ).all()
        histories = defaultdict(list)
        for s in snapshots:
            histories[s.repository_id].append(
                Observation(s.observed_at, s.stars, s.forks, s.contributors, s.commits_7d)
            )
        measurements = {
            (r.id, w): measure(histories[r.id], w, now) for r in repos for w in WINDOW_DAYS
        }
        groups = defaultdict(list)
        for r in repos:
            group = peer_group(r.stars, (now - utc(r.created_at_github)).days)
            for w in WINDOW_DAYS:
                velocity = measurements[r.id, w]["features"]["star_velocity"]
                if velocity is not None and not r.archived and not r.disabled:
                    groups[group, w].append((r.id, velocity))
        for r in repos:
            age = (now - utc(r.created_at_github)).total_seconds() / 86400
            for w in WINDOW_DAYS:
                m = measurements[r.id, w]
                velocity = m["features"]["star_velocity"]
                if velocity is not None:
                    peers = [v for rid, v in groups[peer_group(r.stars, age), w] if rid != r.id]
                    m["features"]["peer_percentile"] = compute_peer_percentile(velocity, peers)
                    m["coverage"]["peer_count"] = len(peers)
                score = compute_momentum_score(m) or compute_early_discovery_score(
                    stars=r.stars,
                    forks=r.forks,
                    age_days=age,
                    days_since_push=(now - utc(r.pushed_at)).total_seconds() / 86400
                    if r.pushed_at
                    else None,
                    archived=r.archived or r.disabled,
                    coverage=m["coverage"],
                )
                statement = (
                    insert_for(session, Score)
                    .values(repository_id=r.id, calculated_at=now, time_window=w, **score)
                    .on_conflict_do_nothing(
                        index_elements=[
                            "repository_id",
                            "time_window",
                            "calculated_at",
                            "scoring_version",
                        ]
                    )
                )
                await session.execute(statement)
                if w == "24h":
                    r.tracking_priority = (
                        "low"
                        if r.archived or r.disabled
                        else "high"
                        if score["score_type"] == "observed_momentum" and score["score"] >= 65
                        else "normal"
                    )
        await session.commit()
        return len(repos)
