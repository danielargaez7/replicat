"""
Tests for cache operations.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from cache import (
    RESULT_PREFIX,
    RESULT_TTL,
    get_cached_result,
    invalidate_cached_result,
    set_cached_result,
)


@pytest.mark.asyncio
async def test_get_cached_result_returns_none_when_no_pool():
    with patch("cache.pool", None):
        result = await get_cached_result("test-id")
        assert result is None


@pytest.mark.asyncio
async def test_get_cached_result_returns_data():
    mock_pool = AsyncMock()
    test_data = {"health_score": 42, "findings": []}
    mock_pool.get.return_value = json.dumps(test_data)

    with patch("cache.pool", mock_pool):
        result = await get_cached_result("test-id")
        assert result == test_data
        mock_pool.get.assert_called_once_with(f"{RESULT_PREFIX}test-id")


@pytest.mark.asyncio
async def test_get_cached_result_returns_none_on_miss():
    mock_pool = AsyncMock()
    mock_pool.get.return_value = None

    with patch("cache.pool", mock_pool):
        result = await get_cached_result("missing-id")
        assert result is None


@pytest.mark.asyncio
async def test_set_cached_result():
    mock_pool = AsyncMock()
    test_data = {"health_score": 85}

    with patch("cache.pool", mock_pool):
        await set_cached_result("test-id", test_data)
        mock_pool.set.assert_called_once_with(
            f"{RESULT_PREFIX}test-id",
            json.dumps(test_data),
            ex=RESULT_TTL,
        )


@pytest.mark.asyncio
async def test_set_cached_result_noop_when_no_pool():
    with patch("cache.pool", None):
        # Should not raise
        await set_cached_result("test-id", {"data": "test"})


@pytest.mark.asyncio
async def test_invalidate_cached_result():
    mock_pool = AsyncMock()

    with patch("cache.pool", mock_pool):
        await invalidate_cached_result("test-id")
        mock_pool.delete.assert_called_once_with(f"{RESULT_PREFIX}test-id")


@pytest.mark.asyncio
async def test_invalidate_noop_when_no_pool():
    with patch("cache.pool", None):
        await invalidate_cached_result("test-id")
