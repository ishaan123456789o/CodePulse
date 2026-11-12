from datetime import timedelta

from sqlalchemy import and_, case, func, literal_column, or_, select
from sqlalchemy.orm import aliased

from app.analytics.engine import utc
from app.core.config import get_settings
from app.models.entities import Repository, Score, Snapshot, WatchlistEntry, utcnow
from app.schemas.api import Filters, Page, RepositoryOut, ScoreOut, SnapshotOut


def ranked_scores(window: str):
    return (
        select(
            Score,
            func.row_number()
            .over(
                partition_by=Score.repository_id,
                order_by=(Score.calculated_at.desc(), Score.id.desc()),
            )
            .label("rn"),
        )
        .where(Score.time_window == window)
        .subquery()
    )


def latest_scores(window: str):
    ranked = ranked_scores(window)
    return aliased(Score, ranked), ranked


def search_condition(session, q: str):
    if session.bind.dialect.name == "postgresql":
        vector = func.to_tsvector(
            literal_column("'simple'"),
            func.coalesce(Repository.name, "")
            + literal_column("' '")
            + func.coalesce(Repository.description, ""),
        )
        # Indexed full-text search; prefix repo names use the btree pattern index.
        return or_(
            vector.op("@@")(func.plainto_tsquery("simple", q)),
            func.lower(Repository.full_name).like(
                q.lower().replace("%", "\\%").replace("_", "\\_") + "%", escape="\\"
            ),
            func.lower(Repository.name).like(
                q.lower().replace("%", "\\%").replace("_", "\\_") + "%", escape="\\"
            ),
        )
    pattern = "%" + q.replace("%", "\\%").replace("_", "\\_") + "%"
    return or_(
        Repository.full_name.ilike(pattern, escape="\\"),
        Repository.description.ilike(pattern, escape="\\"),
    )


def score_out(score: Score | None) -> ScoreOut | None:
    if score is None:
        return None
    out = ScoreOut.model_validate(score)
    out.stale = (utcnow() - utc(score.calculated_at)).total_seconds() > 7200
    return out


async def hydrate(session, rows, window, workspace=None):
    ids = [r.id for r, _ in rows]
    if not ids:
        return []
    # Window function bounds chart samples per repository without an N+1 query.
    ranked = (
        select(
            Snapshot,
            func.row_number()
            .over(partition_by=Snapshot.repository_id, order_by=Snapshot.observed_at.desc())
            .label("rn"),
        )
        .where(Snapshot.repository_id.in_(ids))
        .subquery()
    )
    snap = aliased(Snapshot, ranked)
    snapshots = (
        await session.scalars(select(snap).where(ranked.c.rn <= 30).order_by(snap.observed_at))
    ).all()
    by_repo = {}
    for point in snapshots:
        by_repo.setdefault(point.repository_id, []).append(SnapshotOut.model_validate(point))
    saved = (
        set(
            (
                await session.scalars(
                    select(WatchlistEntry.repository_id).where(
                        WatchlistEntry.workspace_id == workspace,
                        WatchlistEntry.repository_id.in_(ids),
                    )
                )
            ).all()
        )
        if workspace
        else set()
    )
    ranked_previous = ranked_scores(window)
    previous = aliased(Score, ranked_previous)
    prior = {
        s.repository_id: s
        for s in (
            await session.scalars(
                select(previous).where(ranked_previous.c.rn == 2, previous.repository_id.in_(ids))
            )
        ).all()
    }
    result = []
    for r, score in rows:
        out = RepositoryOut.model_validate(r)
        out.score = score_out(score)
        old = prior.get(r.id)
        if (
            old
            and score
            and old.score_type == score.score_type
            and old.scoring_version == score.scoring_version
        ):
            out.score_change = round(score.score - old.score, 2)
        out.sparkline = by_repo.get(r.id, [])
        out.watchlisted = r.id in saved
        result.append(out)
    return result


async def list_repositories(session, filters: Filters, workspace=None, watchlist=False) -> Page:
    score, ranked = latest_scores(filters.time_window)
    query = select(Repository, score).outerjoin(
        score, and_(Repository.id == score.repository_id, ranked.c.rn == 1)
    )
    conditions = [Repository.stars >= filters.min_stars]
    if filters.q:
        conditions.append(search_condition(session, filters.q))
    for name in ["category", "language"]:
        if getattr(filters, name):
            conditions.append(getattr(Repository, name) == getattr(filters, name))
    if filters.max_stars is not None:
        conditions.append(Repository.stars <= filters.max_stars)
    if filters.min_score:
        conditions.append(score.score >= filters.min_score)
    if filters.score_type:
        conditions.extend(
            [
                score.score_type == filters.score_type,
                score.calculated_at >= utcnow() - timedelta(hours=2),
            ]
        )
    if filters.emerging:
        conditions.extend(
            [
                Repository.stars < 10000,
                Repository.archived.is_(False),
                Repository.disabled.is_(False),
            ]
        )
    if filters.new_only:
        conditions.append(Repository.discovered_at >= utcnow() - timedelta(days=7))
    if watchlist:
        conditions.append(
            Repository.id.in_(
                select(WatchlistEntry.repository_id).where(WatchlistEntry.workspace_id == workspace)
            )
        )
    query = query.where(*conditions)
    total = await session.scalar(select(func.count()).select_from(query.subquery()))
    growth = score.feature_breakdown["values"]["star_velocity"].as_float()
    sort = {
        "momentum": score.score.desc().nulls_last(),
        "stars": Repository.stars.desc(),
        "growth": growth.desc().nulls_last(),
        "newest": Repository.discovered_at.desc(),
        "name": Repository.full_name.asc(),
    }[filters.sort]
    score_group = case(
        (score.score_type == "observed_momentum", 0),
        (score.score_type == "early_discovery", 1),
        else_=2,
    )
    ordering = (
        [score_group, sort, Repository.id] if filters.sort == "momentum" else [sort, Repository.id]
    )
    rows = (
        await session.execute(
            query.order_by(*ordering)
            .offset((filters.page - 1) * filters.page_size)
            .limit(filters.page_size)
        )
    ).all()
    return Page(
        items=await hydrate(session, rows, filters.time_window, workspace),
        total=total,
        page=filters.page,
        page_size=filters.page_size,
        demo=get_settings().demo_mode,
    )


async def get_repository(session, repo_id, window, workspace=None):
    score, ranked = latest_scores(window)
    row = (
        await session.execute(
            select(Repository, score)
            .outerjoin(score, and_(Repository.id == score.repository_id, ranked.c.rn == 1))
            .where(Repository.id == repo_id)
        )
    ).first()
    return (await hydrate(session, [row], window, workspace))[0] if row else None
