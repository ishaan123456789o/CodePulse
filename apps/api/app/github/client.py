import asyncio
import json
import random
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any

import httpx
from redis.asyncio import Redis

from app.core.config import Settings


class GitHubError(Exception):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class BudgetExhausted(GitHubError):
    pass


class RateLimited(GitHubError):
    def __init__(self, delay: float):
        self.delay = delay
        super().__init__(f"GitHub cooldown active; retry after {int(delay)} seconds", 429)


@dataclass
class Result:
    data: dict[str, Any] | list[Any] | None
    etag: str | None
    not_modified: bool = False
    has_next: bool = False


class GitHubClient:
    """One serialized, bounded client. All collectors also hold a shared Redis lock."""

    def __init__(self, settings: Settings, redis: Redis, budget: int, transport=None):
        self.settings, self.redis, self.remaining = settings, redis, budget
        self.semaphore = asyncio.Semaphore(1)
        self.last_request = 0.0
        self.http = httpx.AsyncClient(
            base_url="https://api.github.com",
            timeout=20,
            follow_redirects=False,
            transport=transport,
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2026-03-10",
                "Authorization": f"Bearer {settings.github_token.get_secret_value()}",
                "User-Agent": "CodePulse/0.1",
            },
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self.http.aclose()

    async def get(self, path: str, *, params=None, etag: str | None = None) -> Result:
        if not path.startswith("/") or path.startswith("//") or ":" in path:
            raise ValueError("Only fixed GitHub API paths are accepted")
        resource = "search" if path.startswith("/search/") else "core"
        async with self.semaphore:
            for attempt in range(3):
                cooldown = await self.redis.get("github:cooldown")
                quota = await self.redis.get(f"github:quota:{resource}")
                until = float(cooldown or 0)
                if quota:
                    q = json.loads(quota)
                    if q["remaining"] <= 1:
                        until = max(until, q["reset"])
                if until > time.time():
                    raise RateLimited(until - time.time())
                if self.remaining <= 0:
                    raise BudgetExhausted("Per-run GitHub request budget exhausted")
                await asyncio.sleep(
                    max(
                        0,
                        self.settings.github_min_interval_seconds
                        - (time.monotonic() - self.last_request),
                    )
                )
                self.remaining -= 1
                self.last_request = time.monotonic()
                try:
                    response = await self.http.get(
                        path, params=params, headers={"If-None-Match": etag} if etag else {}
                    )
                except httpx.RequestError:
                    if attempt == 2:
                        raise GitHubError("GitHub network request failed") from None
                    await asyncio.sleep(2**attempt + random.random())
                    continue
                headers = response.headers
                if "x-ratelimit-remaining" in headers:
                    actual_resource = headers.get("x-ratelimit-resource", resource)
                    q = {
                        "remaining": int(headers["x-ratelimit-remaining"]),
                        "limit": int(headers.get("x-ratelimit-limit", "0")),
                        "reset": int(headers.get("x-ratelimit-reset", "0")),
                        "observed_at": time.time(),
                    }
                    await self.redis.set(f"github:quota:{actual_resource}", json.dumps(q), ex=86400)
                if response.status_code in (403, 429):
                    delay = 60.0 * (2**attempt)
                    if headers.get("retry-after"):
                        try:
                            delay = max(delay, float(headers["retry-after"]))
                        except ValueError:
                            delay = max(
                                delay,
                                parsedate_to_datetime(headers["retry-after"]).timestamp()
                                - time.time(),
                            )
                    if headers.get("x-ratelimit-remaining") == "0":
                        delay = max(delay, float(headers.get("x-ratelimit-reset", 0)) - time.time())
                    delay += random.uniform(1, 5)
                    await self.redis.set("github:cooldown", time.time() + delay, ex=int(delay) + 1)
                    # Let the next scheduled run retry. Never sleep a worker through a long cooldown.
                    raise RateLimited(delay)
                if response.status_code == 304:
                    return Result(None, etag, not_modified=True)
                if response.status_code >= 500 and attempt < 2:
                    await asyncio.sleep(2**attempt + random.random())
                    continue
                if response.is_error or response.is_redirect:
                    raise GitHubError(
                        f"GitHub returned HTTP {response.status_code}", response.status_code
                    )
                try:
                    return Result(
                        response.json(), headers.get("etag"), has_next="next" in response.links
                    )
                except ValueError:
                    raise GitHubError("GitHub returned malformed JSON") from None
        raise GitHubError("Retry limit exceeded")
