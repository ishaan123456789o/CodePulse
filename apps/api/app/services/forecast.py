"""Daily prospective predictions and delayed, immutable outcome evaluation."""

from collections import defaultdict
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import func, select

from app.analytics.engine import Observation, utc
from app.analytics.forecast import VERSION, predict
from app.core.config import get_settings
from app.models.entities import Forecast, Repository, Snapshot, utcnow
from app.repositories.ingestion import insert_for
from app.schemas.forecast import ForecastOut, ForecastPage, ForecastStatus, ValidationOut


def source(demo: bool) -> str:
    return "synthetic_demo_fixture" if demo else "github_rest"


async def forecast_all(session_factory) -> int:
    now = utcnow()
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    demo = get_settings().demo_mode
    inserted = 0
    async with session_factory() as session:
        after_id = 0
        while True:
            repos = (
                await session.scalars(
                    select(Repository)
                    .where(
                        Repository.id > after_id,
                        Repository.archived.is_(False),
                        Repository.disabled.is_(False),
                    )
                    .order_by(Repository.id)
                    .limit(100)
                )
            ).all()
            if not repos:
                break
            ids = [r.id for r in repos]
            snapshots = (
                await session.scalars(
                    select(Snapshot)
                    .where(
                        Snapshot.repository_id.in_(ids),
                        Snapshot.observed_at >= now - timedelta(days=17),
                        Snapshot.observed_at <= now,
                        Snapshot.created_at <= now,
                        Snapshot.collection_source == source(demo),
                    )
                    .order_by(Snapshot.observed_at)
                )
            ).all()
            histories = defaultdict(list)
            for s in snapshots:
                histories[s.repository_id].append(Observation(s.observed_at, s.stars, s.forks))
            for repo in repos:
                result = predict(histories[repo.id], now)
                if result["prediction"] is None:
                    continue
                values = result["prediction"]
                statement = (
                    insert_for(session, Forecast)
                    .values(
                        repository_id=repo.id,
                        forecast_day=day,
                        issued_at=now,
                        target_at=values["as_of"] + timedelta(days=7),
                        model_version=VERSION,
                        demo=demo,
                        evaluation_status="pending",
                        **values,
                    )
                    .on_conflict_do_nothing(
                        index_elements=["repository_id", "forecast_day", "model_version"]
                    )
                    .returning(Forecast.id)
                )
                if await session.scalar(statement) is not None:
                    inserted += 1
            after_id = repos[-1].id
            await session.commit()
        await evaluate_due(session, now, demo)
        await session.commit()
    return inserted


async def evaluate_due(session, now, demo: bool):
    # Bounded work per run; oldest outcomes first. Predictions are never rewritten.
    due = (
        await session.scalars(
            select(Forecast)
            .where(
                Forecast.target_at <= now,
                Forecast.evaluated_at.is_(None),
                Forecast.demo == demo,
            )
            .order_by(Forecast.target_at, Forecast.id)
            .limit(500)
        )
    ).all()
    for forecast in due:
        outcome = await session.scalar(
            select(Snapshot)
            .where(
                Snapshot.repository_id == forecast.repository_id,
                Snapshot.observed_at >= forecast.target_at,
                Snapshot.observed_at <= utc(forecast.target_at) + timedelta(hours=6),
                Snapshot.observed_at <= now,
                Snapshot.created_at <= now,
                Snapshot.collection_source == source(demo),
            )
            .order_by(Snapshot.observed_at)
            .limit(1)
        )
        if outcome is not None:
            days = (utc(outcome.observed_at) - utc(forecast.as_of)).total_seconds() / 86400
            # Actual boundary may be up to six hours late; report seven-day equivalent.
            forecast.realized_growth = round(
                (outcome.stars - forecast.stars_at_origin) * 7 / days, 2
            )
            forecast.actual_breakout = forecast.realized_growth >= forecast.breakout_threshold
            forecast.outcome_at = outcome.observed_at
            forecast.evaluation_status = "evaluated"
            forecast.evaluated_at = now
        elif utc(now) > utc(forecast.target_at) + timedelta(hours=6):
            forecast.evaluation_status = "unavailable"
            forecast.evaluated_at = now


def output(forecast, repo, now):
    return ForecastOut.model_validate(forecast).model_copy(
        update={
            "full_name": repo.full_name,
            "language": repo.language,
            "stale": utc(now) - utc(forecast.as_of) > timedelta(hours=30),
        }
    )


async def list_forecasts(session, page: int, page_size: int, breakouts_only: bool):
    now, demo = utcnow(), get_settings().demo_mode
    latest = (
        select(Forecast.repository_id, func.max(Forecast.id).label("latest_id"))
        .where(
            Forecast.model_version == VERSION,
            Forecast.demo == demo,
        )
        .group_by(Forecast.repository_id)
        .subquery()
    )
    query = (
        select(Forecast, Repository)
        .join(latest, Forecast.id == latest.c.latest_id)
        .join(Repository, Repository.id == Forecast.repository_id)
        .where(
            Repository.archived.is_(False),
            Repository.disabled.is_(False),
            Forecast.as_of >= now - timedelta(hours=30),
            Forecast.issued_at <= now,
        )
    )
    if breakouts_only:
        query = query.where(Forecast.predicted_breakout.is_(True))
    total = await session.scalar(select(func.count()).select_from(query.subquery()))
    rows = (
        await session.execute(
            query.order_by(Forecast.breakout_ratio.desc(), Forecast.repository_id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return ForecastPage(
        items=[output(f, r, now) for f, r in rows],
        total=total,
        page=page,
        page_size=page_size,
        demo=demo,
        model_version=VERSION,
    )


async def repository_forecast(session, repo_id: int):
    repo = await session.get(Repository, repo_id)
    if repo is None:
        raise HTTPException(404, "Repository not found")
    demo = get_settings().demo_mode
    if repo.archived or repo.disabled:
        return ForecastStatus(
            status="inactive",
            reason="Archived or disabled repositories are not forecast",
            demo=demo,
        )
    row = await session.scalar(
        select(Forecast)
        .where(
            Forecast.repository_id == repo_id,
            Forecast.model_version == VERSION,
            Forecast.demo == demo,
        )
        .order_by(Forecast.id.desc())
        .limit(1)
    )
    if row is None:
        return ForecastStatus(
            status="insufficient_history",
            reason="Awaiting a forecast run with at least 14 days of continuous history and an observation from the last six hours",
            demo=demo,
        )
    item = output(row, repo, utcnow())
    return ForecastStatus(
        status="stale" if item.stale else "ready",
        reason="Awaiting a fresh forecast" if item.stale else None,
        forecast=item,
        demo=demo,
    )


async def validation(session):
    demo = get_settings().demo_mode
    rows = (
        await session.scalars(
            select(Forecast).where(
                Forecast.model_version == VERSION,
                Forecast.demo == demo,
                Forecast.issued_at >= utcnow() - timedelta(days=90),
            )
        )
    ).all()
    evaluated = [r for r in rows if r.evaluation_status == "evaluated"]
    positives = [r for r in evaluated if r.predicted_breakout]
    true_positives = sum(bool(r.actual_breakout) for r in positives)
    actual_positives = sum(bool(r.actual_breakout) for r in evaluated)
    n = len(evaluated)
    return ValidationOut(
        model_version=VERSION,
        demo=demo,
        evaluated=n,
        pending=sum(r.evaluation_status == "pending" for r in rows),
        unavailable=sum(r.evaluation_status == "unavailable" for r in rows),
        predicted_breakouts=len(positives),
        actual_breakouts=actual_positives,
        precision=true_positives / len(positives) if positives else None,
        recall=true_positives / actual_positives if actual_positives else None,
        mean_absolute_error=sum(abs(r.projected_growth - r.realized_growth) for r in evaluated) / n
        if n
        else None,
        baseline_mean_absolute_error=sum(
            abs(r.baseline_growth - r.realized_growth) for r in evaluated
        )
        / n
        if n
        else None,
    )
