"""
Multi-tier caching for Bundlescope.

Cache layers:
- analysis_result:{id}           → Full analysis results (24h TTL)
- llm:{namespace_content_hash}   → Per-namespace LLM responses (48h TTL)
- synthesis:{findings_hash}      → Synthesis LLM responses (24h TTL)
"""

import hashlib
import json
import logging
import os
from typing import Optional

import redis.asyncio as redis

logger = logging.getLogger("bundlescope")

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

pool: Optional[redis.Redis] = None

# TTLs
RESULT_TTL = 60 * 60 * 24       # 24 hours — full analysis results
LLM_CACHE_TTL = 60 * 60 * 48    # 48 hours — per-namespace LLM responses
SYNTHESIS_TTL = 60 * 60 * 24     # 24 hours — synthesis responses

# Key prefixes
RESULT_PREFIX = "analysis_result:"
LLM_PREFIX = "llm:"
SYNTHESIS_PREFIX = "synthesis:"

# Prompt version — increment when you change prompts to invalidate cache
PROMPT_VERSION = "v3"


async def init_cache():
    global pool
    try:
        pool = redis.from_url(REDIS_URL, decode_responses=True)
        await pool.ping()
        logger.info("Redis cache connected")
    except Exception as e:
        logger.warning("Redis unavailable, running without cache: %s", e)
        pool = None


async def close_cache():
    global pool
    if pool:
        await pool.aclose()
        pool = None


# ─── Content Hashing ───

def _hash_content(*parts: str) -> str:
    """Create a stable hash from content strings for cache keys."""
    combined = "|".join(parts)
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


# ─── Full Analysis Result Cache ───

async def get_cached_result(analysis_id: str) -> Optional[dict]:
    if not pool:
        return None
    try:
        data = await pool.get(f"{RESULT_PREFIX}{analysis_id}")
        if data:
            return json.loads(data)
    except Exception as e:
        logger.warning("Cache read error: %s", e)
    return None


async def set_cached_result(analysis_id: str, result: dict):
    if not pool:
        return
    try:
        await pool.set(
            f"{RESULT_PREFIX}{analysis_id}",
            json.dumps(result),
            ex=RESULT_TTL,
        )
    except Exception as e:
        logger.warning("Cache write error: %s", e)


async def invalidate_cached_result(analysis_id: str):
    if not pool:
        return
    try:
        await pool.delete(f"{RESULT_PREFIX}{analysis_id}")
    except Exception as e:
        logger.warning("Cache invalidate error: %s", e)


# ─── Per-Namespace LLM Response Cache ───

def build_llm_cache_key(namespace: str, context_content: str, model: str) -> str:
    """Build a cache key for a per-namespace LLM response."""
    content_hash = _hash_content(namespace, context_content, model, PROMPT_VERSION)
    return f"{LLM_PREFIX}{content_hash}"


async def get_cached_llm_response(cache_key: str) -> Optional[str]:
    """Get a cached LLM response. Returns the raw JSON string."""
    if not pool:
        return None
    try:
        data = await pool.get(cache_key)
        if data:
            logger.info("LLM cache hit: %s", cache_key)
            return data
    except Exception as e:
        logger.warning("LLM cache read error: %s", e)
    return None


async def set_cached_llm_response(cache_key: str, response: str):
    """Cache an LLM response."""
    if not pool:
        return
    try:
        await pool.set(cache_key, response, ex=LLM_CACHE_TTL)
    except Exception as e:
        logger.warning("LLM cache write error: %s", e)


# ─── Synthesis Cache ───

def build_synthesis_cache_key(findings_summary: str, model: str) -> str:
    """Build a cache key for a synthesis response."""
    content_hash = _hash_content(findings_summary, model, PROMPT_VERSION)
    return f"{SYNTHESIS_PREFIX}{content_hash}"


async def get_cached_synthesis(cache_key: str) -> Optional[str]:
    if not pool:
        return None
    try:
        data = await pool.get(cache_key)
        if data:
            logger.info("Synthesis cache hit: %s", cache_key)
            return data
    except Exception as e:
        logger.warning("Synthesis cache read error: %s", e)
    return None


async def set_cached_synthesis(cache_key: str, response: str):
    if not pool:
        return
    try:
        await pool.set(cache_key, response, ex=SYNTHESIS_TTL)
    except Exception as e:
        logger.warning("Synthesis cache write error: %s", e)
