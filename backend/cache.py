import json
import os
from typing import Optional

import redis.asyncio as redis

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

pool: Optional[redis.Redis] = None

RESULT_TTL = 60 * 60 * 24  # 24 hours
RESULT_PREFIX = "analysis_result:"


async def init_cache():
    global pool
    pool = redis.from_url(REDIS_URL, decode_responses=True)


async def close_cache():
    global pool
    if pool:
        await pool.aclose()
        pool = None


async def get_cached_result(analysis_id: str) -> Optional[dict]:
    if not pool:
        return None
    data = await pool.get(f"{RESULT_PREFIX}{analysis_id}")
    if data:
        return json.loads(data)
    return None


async def set_cached_result(analysis_id: str, result: dict):
    if not pool:
        return
    await pool.set(
        f"{RESULT_PREFIX}{analysis_id}",
        json.dumps(result),
        ex=RESULT_TTL,
    )


async def invalidate_cached_result(analysis_id: str):
    if not pool:
        return
    await pool.delete(f"{RESULT_PREFIX}{analysis_id}")
