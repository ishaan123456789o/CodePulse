import os
from datetime import timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.session import get_session
from app.main import app
from app.models.entities import Base, utcnow
from app.repositories.ingestion import record_snapshot, upsert_repository


@pytest.fixture
async def sessions():
    url = os.getenv("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    if not url.endswith("/:memory:") and "test" not in url.rsplit("/", 1)[-1]:
        raise RuntimeError("Destructive integration tests require a database named with 'test'")
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def client(sessions):
    async def override():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_session] = override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


def github_fixture(github_id=10001, stars=100, name="test-project", language="Python"):
    now = utcnow()
    return {
        "id": github_id,
        "owner": {"login": "fixture-org"},
        "name": name,
        "full_name": f"fixture-org/{name}",
        "html_url": f"https://github.com/fixture-org/{name}",
        "description": "Synthetic test fixture for a developer search tool",
        "language": language,
        "topics": ["developer-tools"],
        "created_at": (now - timedelta(days=100)).isoformat(),
        "pushed_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "stargazers_count": stars,
        "forks_count": 10,
        "open_issues_count": 3,
        "archived": False,
        "private": False,
        "disabled": False,
        "license": {"spdx_id": "MIT"},
        "size": 100,
        "default_branch": "main",
    }


@pytest.fixture
async def seeded(sessions):
    now = utcnow().replace(minute=0, second=0, microsecond=0)
    async with sessions() as session:
        repo, _ = await upsert_repository(session, github_fixture(), now)
        for hour, stars in [(-48, 50), (-24, 60), (-12, 75), (0, 100)]:
            repo.stars = stars
            await record_snapshot(session, repo, now + timedelta(hours=hour), 6, "test_fixture")
        await session.commit()
        repo_id = repo.id
    from app.services.scoring import score_all

    await score_all(sessions)
    return repo_id


@pytest.fixture(autouse=True)
def disable_summary_cache(monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "summary_cache_seconds", 0)
