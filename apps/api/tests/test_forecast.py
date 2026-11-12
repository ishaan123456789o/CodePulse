from datetime import datetime, timedelta, timezone

import pytest
from conftest import github_fixture
from sqlalchemy import func, select

from app.analytics.engine import Observation, utc
from app.analytics.forecast import predict
from app.core.config import get_settings
from app.models.entities import Forecast, Repository, Snapshot
from app.repositories.ingestion import record_snapshot, upsert_repository
from app.services import forecast as service

NOW = datetime(2026, 11, 12, 12, tzinfo=timezone.utc)


def history(previous=1, recent=10, initial=100):
    return [
        Observation(
            NOW - timedelta(days=14 - day),
            initial + min(day, 7) * previous + max(0, day - 7) * recent,
            10,
        )
        for day in range(15)
    ]


def test_accelerating_and_flat_predictions_have_explicit_target():
    accelerating = predict(history(), NOW)["prediction"]
    assert accelerating["projected_growth"] == 101.5
    assert accelerating["breakout_threshold"] == 58
    assert accelerating["predicted_breakout"]
    assert accelerating["baseline_growth"] == 70
    flat = predict(history(10, 10), NOW)["prediction"]
    assert flat["projected_growth"] == 70
    assert not flat["predicted_breakout"]
    assert "probability" not in accelerating


def test_future_observations_cannot_change_forecast():
    points = history()
    expected = predict(points, NOW)
    assert (
        predict(points + [Observation(NOW + timedelta(hours=1), 1000000, 10000)], NOW) == expected
    )
    assert predict(list(reversed(points)), NOW) == expected


@pytest.mark.parametrize(
    "points,as_of",
    [
        ([], NOW),
        (history()[1:], NOW),
        (history()[:5] + history()[8:], NOW),
        (history(), NOW + timedelta(hours=7)),
    ],
)
def test_short_stale_and_gappy_histories_are_unavailable(points, as_of):
    result = predict(points, as_of)
    assert result["status"] == "insufficient_history"
    assert result["prediction"] is None
    assert result["reason"]


def test_decline_and_size_threshold():
    decline = predict(history(-1, -5, 500), NOW)["prediction"]
    assert decline["projected_growth"] < 0
    assert not decline["predicted_breakout"]
    assert decline["projected_growth"] >= -decline["stars_at_origin"]
    large = predict(history(1, 10, 100000), NOW)["prediction"]
    assert large["breakout_threshold"] >= 2000
    assert not large["predicted_breakout"]
    quiet = predict(history(0, 0), NOW)["prediction"]
    assert quiet["projected_growth"] == 0
    assert quiet["breakout_threshold"] == 20


async def seed_history(sessions, source="github_rest", github_id=10101, points=None):
    async with sessions() as session:
        repo, _ = await upsert_repository(session, github_fixture(github_id=github_id), NOW)
        for p in history() if points is None else points:
            repo.stars = p.stars
            await record_snapshot(session, repo, p.observed_at, 6, source)
        await session.commit()
        return repo.id


async def test_saved_prediction_api_and_daily_idempotency(client, sessions, monkeypatch):
    monkeypatch.setattr(service, "utcnow", lambda: NOW)
    rid = await seed_history(sessions)
    assert await service.forecast_all(sessions) == 1
    first = (await client.get(f"/api/v1/repositories/{rid}/forecast")).json()
    assert first["status"] == "ready"
    assert first["forecast"]["projected_growth"] == 101.5
    async with sessions() as session:
        repo = await session.get(Repository, rid)
        repo.stars = 999999
        await session.commit()
    assert await service.forecast_all(sessions) == 0
    assert (await client.get(f"/api/v1/repositories/{rid}/forecast")).json() == first
    listing = (await client.get("/api/v1/forecast?breakouts_only=true")).json()
    assert listing["total"] == 1
    assert listing["items"][0]["repository_id"] == rid
    assert not listing["demo"]
    assert (await client.get("/api/v1/forecast?page=0")).status_code == 422
    assert (await client.get("/api/v1/forecast?page_size=101")).status_code == 422
    assert (await client.get("/api/v1/repositories/999/forecast")).status_code == 404
    metrics = (await client.get("/api/v1/forecast/validation")).json()
    assert metrics["pending"] == 1 and metrics["evaluated"] == 0
    assert metrics["precision"] is None and metrics["mean_absolute_error"] is None
    monkeypatch.setattr(service, "utcnow", lambda: NOW + timedelta(hours=31))
    assert (await client.get("/api/v1/forecast")).json()["total"] == 0
    assert (await client.get(f"/api/v1/repositories/{rid}/forecast")).json()["status"] == "stale"
    async with sessions() as session:
        assert await session.scalar(select(func.count(Forecast.id))) == 1


async def test_outcomes_are_delayed_and_predictions_are_preserved(client, sessions, monkeypatch):
    monkeypatch.setattr(service, "utcnow", lambda: NOW)
    rid = await seed_history(sessions)
    await service.forecast_all(sessions)
    target = NOW + timedelta(days=7)
    async with sessions() as session:
        repo = await session.get(Repository, rid)
        repo.stars = 277
        await record_snapshot(session, repo, target, 6)
        await session.commit()
    await service.forecast_all(sessions)
    assert (await client.get("/api/v1/forecast/validation")).json()["evaluated"] == 0
    monkeypatch.setattr(service, "utcnow", lambda: target)
    await service.forecast_all(sessions)
    async with sessions() as session:
        f = await session.scalar(select(Forecast))
        assert f.projected_growth == 101.5
        assert f.realized_growth == 100
        assert f.actual_breakout is True
        assert utc(f.issued_at) == NOW
    v = (await client.get("/api/v1/forecast/validation")).json()
    assert v["evaluated"] == 1 and v["precision"] == 1 and v["recall"] == 1
    assert v["mean_absolute_error"] == 1.5
    assert v["baseline_mean_absolute_error"] == 30
    await service.forecast_all(sessions)
    assert (await client.get("/api/v1/forecast/validation")).json() == v


async def test_missing_outcome_not_counted_as_failure(client, sessions, monkeypatch):
    monkeypatch.setattr(service, "utcnow", lambda: NOW)
    await seed_history(sessions)
    await service.forecast_all(sessions)
    monkeypatch.setattr(service, "utcnow", lambda: NOW + timedelta(days=7, hours=7))
    await service.forecast_all(sessions)
    v = (await client.get("/api/v1/forecast/validation")).json()
    assert v["unavailable"] == 1 and v["evaluated"] == 0
    assert v["precision"] is None


async def test_source_isolation_inactive_and_cold_start(client, sessions, monkeypatch):
    monkeypatch.setattr(service, "utcnow", lambda: NOW)
    rid = await seed_history(sessions, source="synthetic_demo_fixture")
    assert await service.forecast_all(sessions) == 0
    assert (await client.get(f"/api/v1/repositories/{rid}/forecast")).json()[
        "status"
    ] == "insufficient_history"
    monkeypatch.setattr(get_settings(), "demo_mode", True)
    assert await service.forecast_all(sessions) == 1
    assert (await client.get("/api/v1/forecast")).json()["demo"] is True
    monkeypatch.setattr(get_settings(), "demo_mode", False)
    assert (await client.get("/api/v1/forecast")).json()["total"] == 0
    async with sessions() as session:
        repo = await session.get(Repository, rid)
        repo.archived = True
        await session.commit()
    assert (await client.get(f"/api/v1/repositories/{rid}/forecast")).json()["status"] == "inactive"
    assert await service.forecast_all(sessions) == 0


async def test_late_inserted_history_cannot_leak(sessions, monkeypatch):
    monkeypatch.setattr(service, "utcnow", lambda: NOW)
    await seed_history(sessions)
    async with sessions() as session:
        point = await session.scalar(select(Snapshot).order_by(Snapshot.observed_at))
        point.created_at = NOW + timedelta(hours=1)
        await session.commit()
    assert await service.forecast_all(sessions) == 0


async def test_pagination_latest_only_and_breakout_filter(client, sessions, monkeypatch):
    monkeypatch.setattr(service, "utcnow", lambda: NOW)
    for i in range(3):
        await seed_history(
            sessions, github_id=30000 + i, points=history(recent=1 if i == 2 else 10)
        )
    assert await service.forecast_all(sessions) == 3
    first = (await client.get("/api/v1/forecast?page_size=1")).json()
    second = (await client.get("/api/v1/forecast?page_size=1&page=2")).json()
    assert first["total"] == 3
    assert first["items"][0]["id"] != second["items"][0]["id"]
    assert (await client.get("/api/v1/forecast?breakouts_only=true")).json()["total"] == 2


async def test_new_day_saves_new_forecast_but_lists_only_latest(client, sessions, monkeypatch):
    monkeypatch.setattr(service, "utcnow", lambda: NOW)
    rid = await seed_history(sessions)
    await service.forecast_all(sessions)
    tomorrow = NOW + timedelta(days=1)
    async with sessions() as session:
        repo = await session.get(Repository, rid)
        repo.stars = 200
        await record_snapshot(session, repo, tomorrow, 6)
        await session.commit()
    monkeypatch.setattr(service, "utcnow", lambda: tomorrow)
    assert await service.forecast_all(sessions) == 1
    listing = (await client.get("/api/v1/forecast")).json()
    assert listing["total"] == 1
    assert datetime.fromisoformat(listing["items"][0]["issued_at"]) == tomorrow
    async with sessions() as session:
        assert await session.scalar(select(func.count(Forecast.id))) == 2
        original = await session.scalar(select(Forecast).order_by(Forecast.id))
        assert original.projected_growth == 101.5


@pytest.mark.parametrize("hours,expected_status", [(6, "evaluated"), (7, "unavailable")])
async def test_outcome_tolerance_and_elapsed_time_normalization(
    sessions, monkeypatch, hours, expected_status
):
    monkeypatch.setattr(service, "utcnow", lambda: NOW)
    rid = await seed_history(sessions)
    await service.forecast_all(sessions)
    observed = NOW + timedelta(days=7, hours=hours)
    async with sessions() as session:
        repo = await session.get(Repository, rid)
        repo.stars = 250
        await record_snapshot(session, repo, observed, 6)
        await session.commit()
    monkeypatch.setattr(service, "utcnow", lambda: observed)
    await service.forecast_all(sessions)
    async with sessions() as session:
        forecast = await session.scalar(select(Forecast).order_by(Forecast.id))
        assert forecast.evaluation_status == expected_status
        if hours == 6:
            assert forecast.realized_growth == round(73 * 7 / 7.25, 2)
        else:
            assert forecast.realized_growth is None
