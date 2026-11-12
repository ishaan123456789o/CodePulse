import asyncio
import json
import time

import structlog
from celery import Celery
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.github.client import GitHubClient
from app.services.ingestion import discover, recover_jobs, track

settings = get_settings()
celery = Celery("codepulse", broker=settings.redis_url)
celery.conf.update(
    timezone="UTC",
    enable_utc=True,
    task_serializer="json",
    accept_content=["json"],
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_soft_time_limit=3200,
    task_time_limit=3300,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "discovery": {
            "task": "codepulse.discover",
            "schedule": settings.discovery_interval_seconds,
            "options": {"expires": 1800},
        },
        "tracking": {"task": "codepulse.track", "schedule": 300, "options": {"expires": 280}},
        "scoring": {"task": "codepulse.score", "schedule": 3600, "options": {"expires": 3500}},
        "recovery": {"task": "codepulse.recover", "schedule": 3600},
    },
)
log = structlog.get_logger()


async def run(kind: str):
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    lock = redis.lock(
        "codepulse:collector" if kind in ("discover", "track") else f"codepulse:{kind}",
        timeout=3500,
        blocking_timeout=0,
    )
    acquired = False
    try:
        acquired = await lock.acquire(blocking=False)
        if not acquired:
            return {"status": "already_running"}
        await redis.set("codepulse:worker_heartbeat", time.time(), ex=7200)
        if kind in ("discover", "track") and (not settings.github_configured or settings.demo_mode):
            return {"status": "demo" if settings.demo_mode else "unconfigured"}
        await redis.set(
            f"codepulse:task:{kind}",
            json.dumps({"status": "running", "at": time.time()}),
            ex=172800,
        )
        if kind in ("discover", "track"):
            budget = (
                settings.discovery_request_budget
                if kind == "discover"
                else settings.tracking_request_budget
            )
            async with GitHubClient(settings, redis, budget) as client:
                if kind == "discover":
                    rotation = await redis.incr("codepulse:discovery_rotation")
                    result = await discover(sessions, client, settings, rotation)
                else:
                    result = await track(sessions, client, settings)
            from app.services.scoring import score_all

            await score_all(sessions)
        elif kind == "score":
            from app.services.scoring import score_all

            result = await score_all(sessions)
        else:
            await recover_jobs(sessions)
            result = 0
        await redis.set(
            f"codepulse:task:{kind}",
            json.dumps({"status": "completed", "at": time.time(), "count": result}),
            ex=172800,
        )
        return {"status": "completed", "count": result}
    except Exception as exc:
        log.error("worker_failed", kind=kind, error_type=type(exc).__name__)
        await redis.set(
            f"codepulse:task:{kind}",
            json.dumps({"status": "failed", "at": time.time(), "error": type(exc).__name__}),
            ex=172800,
        )
        raise
    finally:
        if acquired:
            await lock.release()
        await engine.dispose()
        await redis.aclose()


@celery.task(name="codepulse.discover")
def discovery_task():
    return asyncio.run(run("discover"))


@celery.task(name="codepulse.track")
def tracking_task():
    return asyncio.run(run("track"))


@celery.task(name="codepulse.score")
def scoring_task():
    return asyncio.run(run("score"))


@celery.task(name="codepulse.recover")
def recovery_task():
    return asyncio.run(run("recover"))
