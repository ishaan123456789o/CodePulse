import json
import time
from datetime import timedelta

from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import func, select, text

from app.core.config import get_settings
from app.models.entities import DiscoveryRun, IngestionJob, utcnow
from app.schemas.api import StatusOut


def redis_client():
    return Redis.from_url(
        get_settings().redis_url, decode_responses=True, socket_connect_timeout=1, socket_timeout=1
    )


async def readiness(session):
    await session.execute(text("SELECT 1"))
    async with redis_client() as redis:
        await redis.ping()


async def status(session):
    settings = get_settings()
    redis_status, heartbeat, cooldown, quotas, tasks = "unavailable", None, None, {}, {}
    try:
        async with redis_client() as redis:
            await redis.ping()
            redis_status = "healthy"
            heartbeat_raw = await redis.get("codepulse:worker_heartbeat")
            heartbeat = float(heartbeat_raw) if heartbeat_raw else None
            cooldown_raw = await redis.get("github:cooldown")
            cooldown = float(cooldown_raw) if cooldown_raw else None
            for resource in ["core", "search"]:
                raw = await redis.get(f"github:quota:{resource}")
                if raw:
                    quotas[resource] = json.loads(raw)
            for kind in ["discover", "track", "score"]:
                raw = await redis.get(f"codepulse:task:{kind}")
                if raw:
                    tasks[kind] = json.loads(raw)
    except (OSError, ValueError, RedisError):
        pass
    last = await session.scalar(
        select(DiscoveryRun).order_by(DiscoveryRun.started_at.desc()).limit(1)
    )
    failures = await session.scalar(
        select(func.count(IngestionJob.id)).where(
            IngestionJob.status == "failed", IngestionJob.started_at >= utcnow() - timedelta(days=1)
        )
    )
    healthy = heartbeat is not None and time.time() - heartbeat < 900
    ingestion = (
        "demo"
        if settings.demo_mode
        else "unconfigured"
        if not settings.github_configured
        else "rate_limited"
        if cooldown and cooldown > time.time()
        else "degraded"
        if not healthy
        or redis_status != "healthy"
        or failures
        or (last and last.status == "failed")
        else "active"
    )
    return StatusOut(
        ingestion=ingestion,
        github_configured=settings.github_configured,
        demo=settings.demo_mode,
        redis=redis_status,
        worker_last_seen=heartbeat,
        worker_healthy=healthy,
        cooldown_until=cooldown,
        quotas=quotas,
        tasks=tasks,
        last_discovery={
            "status": last.status,
            "started_at": last.started_at.isoformat(),
            "completed_at": last.completed_at.isoformat() if last.completed_at else None,
            "repositories_found": last.repositories_found,
            "error": last.error_message,
        }
        if last
        else None,
        recent_failures=failures,
        cadences_hours={
            "high": settings.track_high_hours,
            "normal": settings.track_normal_hours,
            "low": settings.track_low_hours,
        },
        budgets={
            "discovery": settings.discovery_request_budget,
            "tracking": settings.tracking_request_budget,
        },
    )
