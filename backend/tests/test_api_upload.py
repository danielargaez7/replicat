"""
Tests for the upload API endpoints.
"""

import io

import pytest
import pytest_asyncio


@pytest.mark.asyncio
async def test_upload_valid_bundle(client, sample_upload_file):
    content, filename = sample_upload_file
    response = await client.post(
        "/api/upload",
        files={"file": (filename, io.BytesIO(content), "application/gzip")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "analysis_id" in data
    assert data["filename"] == filename
    assert data["size_bytes"] > 0


@pytest.mark.asyncio
async def test_upload_rejects_wrong_extension(client):
    response = await client.post(
        "/api/upload",
        files={"file": ("malware.exe", io.BytesIO(b"bad data"), "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "Invalid file" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_rejects_empty_filename(client):
    response = await client.post(
        "/api/upload",
        files={"file": ("", io.BytesIO(b"data"), "application/gzip")},
    )
    assert response.status_code in (400, 422)  # FastAPI may reject at validation level


@pytest.mark.asyncio
async def test_upload_rejects_no_file(client):
    response = await client.post("/api/upload")
    assert response.status_code == 422  # FastAPI validation error


@pytest.mark.asyncio
async def test_list_analyses_empty(client):
    response = await client.get("/api/analyses")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_analyses_after_upload(client, sample_upload_file):
    content, filename = sample_upload_file
    await client.post(
        "/api/upload",
        files={"file": (filename, io.BytesIO(content), "application/gzip")},
    )
    response = await client.get("/api/analyses")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["filename"] == filename


@pytest.mark.asyncio
async def test_get_analysis_metadata_not_found(client):
    response = await client.get("/api/analyses/550e8400-e29b-41d4-a716-446655440000")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_analysis_metadata_invalid_uuid(client):
    response = await client.get("/api/analyses/not-a-uuid")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_analysis_metadata_after_upload(client, sample_upload_file):
    content, filename = sample_upload_file
    upload_resp = await client.post(
        "/api/upload",
        files={"file": (filename, io.BytesIO(content), "application/gzip")},
    )
    analysis_id = upload_resp.json()["analysis_id"]
    response = await client.get(f"/api/analyses/{analysis_id}")
    assert response.status_code == 200
    assert response.json()["id"] == analysis_id
    assert response.json()["status"] == "pending"
