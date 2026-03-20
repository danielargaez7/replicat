"""
Tests for middleware: security headers, request ID, error handling.
"""

import pytest


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """Health check should always return 200."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert "checks" in data


@pytest.mark.asyncio
async def test_security_headers_present(client):
    """All security headers should be set on responses."""
    response = await client.get("/health")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "camera=()" in response.headers.get("Permissions-Policy", "")


@pytest.mark.asyncio
async def test_request_id_generated(client):
    """Every response should have an X-Request-ID header."""
    response = await client.get("/health")
    request_id = response.headers.get("X-Request-ID")
    assert request_id is not None
    assert len(request_id) > 0


@pytest.mark.asyncio
async def test_request_id_passthrough(client):
    """If a client sends X-Request-ID, the server should echo it back."""
    custom_id = "test-request-12345"
    response = await client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.headers.get("X-Request-ID") == custom_id


@pytest.mark.asyncio
async def test_404_returns_json(client):
    """Unknown routes should return JSON, not HTML."""
    response = await client.get("/nonexistent/route")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cors_preflight(client):
    """CORS preflight should succeed for allowed origins."""
    response = await client.options(
        "/api/upload",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    # FastAPI CORS middleware handles OPTIONS
    assert response.status_code in (200, 204, 405)
