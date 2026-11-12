import json
import time
from unittest.mock import AsyncMock

import httpx
import pytest
from conftest import github_fixture
from pydantic import SecretStr
from sqlalchemy import select

from app.core.config import Settings
from app.github.client import BudgetExhausted, GitHubClient, GitHubError, RateLimited
from app.github.discovery import discovery_queries
from app.models.entities import DiscoveryRun, Repository, Snapshot, utcnow
from app.services.ingestion import discover, track


class MemoryRedis:
    def __init__(self):
        self.data = {}

    async def get(self, key):
        return self.data.get(key)

    async def set(self, key, value, **kwargs):
        self.data[key] = str(value)


@pytest.fixture
def settings():
    return Settings(
        github_token=SecretStr("test-token"),
        discovery_request_budget=3,
        tracking_request_budget=3,
        discovery_topics=["developer-tools"],
    )


async def test_budget_conditional_and_resource_tracking(settings, monkeypatch):
    monkeypatch.setattr("app.github.client.asyncio.sleep", AsyncMock())
    redis = MemoryRedis()

    def handler(request):
        assert request.headers["if-none-match"] == '"saved"'
        return httpx.Response(
            304,
            headers={
                "x-ratelimit-resource": "core",
                "x-ratelimit-remaining": "42",
                "x-ratelimit-reset": "9999999999",
            },
        )

    async with GitHubClient(settings, redis, 1, httpx.MockTransport(handler)) as client:
        assert (await client.get("/repositories/1", etag='"saved"')).not_modified
        assert json.loads(redis.data["github:quota:core"])["remaining"] == 42
        with pytest.raises(BudgetExhausted):
            await client.get("/repositories/1")


async def test_rate_limit_is_shared_and_no_retry_storm(settings, monkeypatch):
    monkeypatch.setattr("app.github.client.asyncio.sleep", AsyncMock())
    redis, calls = MemoryRedis(), []

    def handler(request):
        calls.append(request)
        return httpx.Response(429, headers={"retry-after": "120"})

    async with GitHubClient(settings, redis, 5, httpx.MockTransport(handler)) as client:
        for _ in range(2):
            with pytest.raises(RateLimited):
                await client.get("/search/repositories")
    assert len(calls) == 1
    assert float(redis.data["github:cooldown"]) >= time.time() + 119


async def test_retries_are_bounded(settings, monkeypatch):
    monkeypatch.setattr("app.github.client.asyncio.sleep", AsyncMock())
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(503)

    async with GitHubClient(settings, MemoryRedis(), 10, httpx.MockTransport(handler)) as client:
        with pytest.raises(GitHubError):
            await client.get("/repositories/1")
        with pytest.raises(ValueError):
            await client.get("https://evil.invalid")
    assert len(calls) == 3


async def test_discovery_then_tracking_is_real_snapshot_boundary(sessions, settings, monkeypatch):
    monkeypatch.setattr("app.github.client.asyncio.sleep", AsyncMock())

    def handler(request):
        return httpx.Response(
            200,
            json={"items": [github_fixture()]}
            if request.url.path.startswith("/search/")
            else github_fixture(),
            headers={"etag": '"v1"'},
        )

    async with GitHubClient(settings, MemoryRedis(), 3, httpx.MockTransport(handler)) as client:
        assert await discover(sessions, client, settings, 1) == 1
        async with sessions() as session:
            assert await session.scalar(select(Snapshot)) is None
        assert await track(sessions, client, settings) == 1
    async with sessions() as session:
        assert (await session.scalar(select(Snapshot))).stars == 100
        assert (await session.scalar(select(Repository))).etag == '"v1"'
        assert (await session.scalar(select(DiscoveryRun))).status == "completed"


def test_rotating_queries(settings):
    first = discovery_queries(utcnow(), 0, settings.discovery_topics)
    second = discovery_queries(utcnow(), 1, settings.discovery_topics)
    assert first != second
    assert "stars:10..2000" in first[0][0]


async def test_optional_activity_is_complete_or_preserved(sessions, settings, monkeypatch):
    from app.github.enrichment import enrich_activity
    from app.repositories.ingestion import upsert_repository

    monkeypatch.setattr("app.github.client.asyncio.sleep", AsyncMock())
    async with sessions() as session:
        repo, _ = await upsert_repository(session, github_fixture(), utcnow())
        transport = httpx.MockTransport(
            lambda request: httpx.Response(
                200, json=[{"author": {"login": "alice"}}, {"author": {"login": "bob"}}]
            )
        )
        async with GitHubClient(settings, MemoryRedis(), 3, transport) as client:
            assert await enrich_activity(client, repo)
        assert repo.commits_7d == 2 and repo.contributors == 2
        failed = httpx.MockTransport(lambda request: httpx.Response(404))
        async with GitHubClient(settings, MemoryRedis(), 3, failed) as client:
            assert not await enrich_activity(client, repo)
        assert repo.commits_7d == 2
        paginated = httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json=[{"author": {"login": "alice"}}],
                headers={
                    "link": '<https://api.github.com/repos/fixture-org/test-project/commits?page=3>; rel="next"'
                },
            )
        )
        async with GitHubClient(settings, MemoryRedis(), 3, paginated) as client:
            assert not await enrich_activity(client, repo)
        assert repo.commits_7d == 2


async def test_invalid_github_metadata_does_not_enter_database(sessions, settings, monkeypatch):
    from sqlalchemy import func

    monkeypatch.setattr("app.github.client.asyncio.sleep", AsyncMock())
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"items": [{"id": 1, "name": "incomplete"}]})
    )
    async with GitHubClient(settings, MemoryRedis(), 3, transport) as client:
        assert await discover(sessions, client, settings, 0) == 0
    async with sessions() as session:
        assert await session.scalar(select(func.count(Repository.id))) == 0
        run = await session.scalar(select(DiscoveryRun))
        assert run.status == "failed"
        assert "invalid" in run.error_message
