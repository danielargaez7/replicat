"""
Tests for the analysis API endpoints.
"""

import pytest


@pytest.mark.asyncio
async def test_get_analysis_not_found(client):
    response = await client.get("/api/analysis/550e8400-e29b-41d4-a716-446655440000")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_analysis_invalid_uuid(client):
    response = await client.get("/api/analysis/not-a-uuid")
    assert response.status_code == 400
    assert "Invalid analysis ID" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_analysis_sql_injection(client):
    response = await client.get("/api/analysis/'; DROP TABLE analyses; --")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_logs_invalid_uuid(client):
    response = await client.get("/api/analysis/not-valid/logs?path=test.log")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_logs_not_found(client):
    response = await client.get(
        "/api/analysis/550e8400-e29b-41d4-a716-446655440000/logs?path=test.log"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_file_tree_not_found(client):
    response = await client.get("/api/analysis/550e8400-e29b-41d4-a716-446655440000/files")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_stream_not_found(client):
    response = await client.get("/api/analysis/550e8400-e29b-41d4-a716-446655440000/stream")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_stream_invalid_uuid(client):
    response = await client.get("/api/analysis/not-a-valid-uuid/stream")
    assert response.status_code == 400
