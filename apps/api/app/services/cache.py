from hashlib import sha256

from redis.exceptions import RedisError

from app.core.config import get_settings
from app.schemas.api import SummaryOut
from app.services.status import redis_client


async def cached_summary(session, window):
    from app.services.catalog import summary

    settings = get_settings()
    if not settings.summary_cache_seconds:
        return await summary(session, window)
    database = sha256(settings.database_url.encode()).hexdigest()[:12]
    key = f"codepulse:summary:{database}:{settings.demo_mode}:{window}"
    try:
        async with redis_client() as redis:
            value = await redis.get(key)
            if value:
                return SummaryOut.model_validate_json(value)
    except (RedisError, OSError, ValueError):
        pass
    result = await summary(session, window)
    try:
        async with redis_client() as redis:
            await redis.set(key, result.model_dump_json(), ex=settings.summary_cache_seconds)
    except (RedisError, OSError):
        pass
    return result
