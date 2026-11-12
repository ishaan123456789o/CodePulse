import uuid

from conftest import github_fixture
from sqlalchemy import func, select

from app.models.entities import Repository, Score, Snapshot, utcnow
from app.repositories.ingestion import record_snapshot, upsert_repository
from app.services.scoring import score_all


async def test_health_empty_and_validation(client):
    assert (await client.get("/api/v1/health")).json()["status"] == "ok"
    response = await client.get("/api/v1/repositories")
    assert response.status_code == 200
    assert response.json()["items"] == []
    assert (await client.get("/api/v1/repositories?page=0")).status_code == 422
    assert (await client.get("/api/v1/repositories?min_stars=100&max_stars=1")).status_code == 422
    assert (await client.get("/api/v1/repositories/999")).status_code == 404
    assert (await client.get("/api/v1/repositories?sort=injected")).status_code == 422
    assert (await client.get("/api/v1/watchlist")).status_code == 400
    assert (await client.post("/api/v1/ingest")).status_code == 404


async def test_catalog_metrics_and_watchlist(client, seeded):
    base = "/api/v1"
    response = await client.get(f"{base}/repositories/{seeded}")
    assert response.status_code == 200
    assert response.json()["score"]["score_type"] == "observed_momentum"
    assert response.json()["score"]["feature_breakdown"]["values"]["star_growth"] == 40
    assert (
        len(
            (await client.get(f"{base}/repositories/{seeded}/history?time_window=all")).json()[
                "observations"
            ]
        )
        == 4
    )
    assert (await client.get(f"{base}/repositories/{seeded}/metrics?time_window=30d")).json()[
        "features"
    ]["star_velocity"] is None
    assert (await client.get(f"{base}/search?q=developer")).json()["total"] == 1
    assert (await client.get(f"{base}/search?q=test-project")).json()["total"] == 1
    assert (await client.get(f"{base}/search?q=test-pro")).json()["total"] == 1
    assert (await client.get(f"{base}/search?q=does-not-exist")).json()["total"] == 0
    assert (await client.get(f"{base}/repositories?language=Rust")).json()["total"] == 0
    assert (await client.get(f"{base}/trending?time_window=24h")).json()["total"] == 1
    assert (await client.get(f"{base}/trending?time_window=7d")).json()["total"] == 0
    summary = (await client.get(f"{base}/dashboard/summary")).json()
    assert summary["repositories_tracked"] == 1
    assert summary["fastest_growing"][0]["id"] == seeded
    workspace = {"X-Workspace-Id": str(uuid.uuid4())}
    for _ in range(2):
        assert (
            await client.post(
                f"{base}/watchlist", headers=workspace, json={"repository_id": seeded}
            )
        ).status_code == 201
    saved = (await client.get(f"{base}/watchlist", headers=workspace)).json()
    assert saved["total"] == 1 and saved["items"][0]["watchlisted"]
    assert (
        await client.get(f"{base}/watchlist", headers={"X-Workspace-Id": str(uuid.uuid4())})
    ).json()["total"] == 0
    assert (await client.delete(f"{base}/watchlist/{seeded}", headers=workspace)).status_code == 204
    assert (await client.get(f"{base}/watchlist", headers=workspace)).json()["total"] == 0
    assert (
        await client.post(f"{base}/watchlist", headers=workspace, json={"repository_id": 999})
    ).status_code == 404


async def test_identity_and_snapshot_idempotency(sessions):
    now = utcnow()
    async with sessions() as session:
        repo, inserted = await upsert_repository(session, github_fixture(), now)
        assert inserted
        original = repo.id
        await record_snapshot(session, repo, now, 6)
        renamed = github_fixture(name="renamed-project", stars=150)
        repo, inserted = await upsert_repository(session, renamed, now)
        assert repo.id == original and not inserted
        await record_snapshot(session, repo, now, 1)
        await session.commit()
        assert await session.scalar(select(func.count(Repository.id))) == 1
        assert await session.scalar(select(func.count(Snapshot.id))) == 1
        snapshot = await session.scalar(select(Snapshot))
        assert snapshot.stars == 100
        assert repo.full_name.endswith("renamed-project")


async def test_scoring_retry_safe(sessions, seeded):
    await score_all(sessions)
    await score_all(sessions)
    async with sessions() as session:
        assert await session.scalar(select(func.count(Score.id))) == 3


async def test_pagination_and_sort(client, sessions):
    async with sessions() as session:
        for i in range(6):
            await upsert_repository(
                session,
                github_fixture(github_id=20000 + i, stars=10 + i, name=f"page-{i}"),
                utcnow(),
            )
        await session.commit()
    first = (await client.get("/api/v1/repositories?sort=stars&page_size=3")).json()
    second = (await client.get("/api/v1/repositories?sort=stars&page_size=3&page=2")).json()
    assert first["total"] == 6
    assert first["items"][0]["stars"] == 15
    assert not {p["id"] for p in first["items"]} & {p["id"] for p in second["items"]}


async def test_private_repositories_rejected(sessions):
    import pytest

    async with sessions() as session:
        with pytest.raises(ValueError):
            await upsert_repository(session, {**github_fixture(), "private": True}, utcnow())


async def test_no_token_status_and_redis_outage(client, monkeypatch):
    from unittest.mock import AsyncMock

    from pydantic import SecretStr
    from redis.exceptions import ConnectionError

    from app.core.config import get_settings
    from app.services import status as status_service

    monkeypatch.setattr(get_settings(), "github_token", SecretStr(""))
    broken = AsyncMock()
    broken.__aenter__.return_value = broken
    broken.ping.side_effect = ConnectionError("test-only Redis failure")
    monkeypatch.setattr(status_service, "redis_client", lambda: broken)
    response = await client.get("/api/v1/system/status")
    assert response.status_code == 200
    assert response.json()["ingestion"] == "unconfigured"
    assert response.json()["redis"] == "unavailable"
    assert (await client.get("/api/v1/health/ready")).status_code == 503


async def test_stale_job_recovery(sessions):
    from datetime import timedelta

    from app.models.entities import DiscoveryRun, IngestionJob
    from app.services.ingestion import recover_jobs

    async with sessions() as session:
        session.add(IngestionJob(job_type="snapshot", started_at=utcnow() - timedelta(hours=3)))
        session.add(DiscoveryRun(query="test", started_at=utcnow() - timedelta(hours=3)))
        await session.commit()
    await recover_jobs(sessions)
    async with sessions() as session:
        assert (await session.scalar(select(IngestionJob))).status == "interrupted"
        assert (await session.scalar(select(DiscoveryRun))).status == "interrupted"


async def test_score_types_rank_separately(client, sessions, seeded):
    async with sessions() as session:
        await upsert_repository(
            session, github_fixture(github_id=20202, name="fresh", stars=9000), utcnow()
        )
        await session.commit()
    await score_all(sessions)
    rows = (await client.get("/api/v1/repositories?sort=momentum")).json()["items"]
    assert rows[0]["score"]["score_type"] == "observed_momentum"
    assert rows[1]["score"]["score_type"] == "early_discovery"
