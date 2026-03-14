from redis.asyncio import Redis

from app.core.config import settings


redis_client = Redis.from_url(settings.redis_url, decode_responses=True)


def trial_used_key(telegram_id: int) -> str:
    return f"trial:used:{telegram_id}"


async def mark_trial_used(telegram_id: int):
    await redis_client.set(trial_used_key(telegram_id), "1")


async def has_trial_used(telegram_id: int) -> bool:
    return bool(await redis_client.get(trial_used_key(telegram_id)))
