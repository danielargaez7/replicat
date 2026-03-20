"""
Tests for the chat API endpoints.
"""

import pytest


@pytest.mark.asyncio
async def test_chat_analysis_not_found(client):
    response = await client.post(
        "/api/analysis/550e8400-e29b-41d4-a716-446655440000/chat",
        json={"message": "hello"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_chat_invalid_uuid(client):
    response = await client.post(
        "/api/analysis/not-a-uuid/chat",
        json={"message": "hello"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_chat_empty_message(client):
    response = await client.post(
        "/api/analysis/550e8400-e29b-41d4-a716-446655440000/chat",
        json={"message": ""},
    )
    # Pydantic min_length=1 validation
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_message_too_long(client):
    response = await client.post(
        "/api/analysis/550e8400-e29b-41d4-a716-446655440000/chat",
        json={"message": "x" * 5000},
    )
    # Pydantic max_length=4000 validation
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_missing_body(client):
    response = await client.post(
        "/api/analysis/550e8400-e29b-41d4-a716-446655440000/chat",
    )
    assert response.status_code == 422
