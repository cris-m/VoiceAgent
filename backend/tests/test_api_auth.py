from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_no_auth_when_api_key_not_set(client):
    """Test that endpoints are accessible when API_KEY is not set."""
    with patch("config.settings.settings.API_KEY", None):
        response = client.get("/api/v1/health")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_endpoint_no_auth():
    """Test that health endpoint is always accessible."""
    from fastapi.testclient import TestClient

    from config.settings import settings
    from main import create_app

    if settings.API_KEY:
        pytest.skip("Requires API_KEY to be unset for this test")

    app = create_app()
    client = TestClient(app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_invalid_bearer_token_returns_401():
    """Test that invalid bearer token is rejected."""
    from unittest.mock import patch

    from fastapi.testclient import TestClient

    from main import create_app

    with patch("config.settings.settings.API_KEY", "test-secret-key"):
        app = create_app()
        client = TestClient(app)

        response = client.get(
            "/api/v1/agent/assistants",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["error"]["message"]


@pytest.mark.asyncio
async def test_valid_bearer_token_allowed():
    """Test that valid bearer token is accepted."""
    from unittest.mock import AsyncMock, patch

    from fastapi.testclient import TestClient

    from main import create_app

    test_key = "test-secret-key"

    with patch("config.settings.settings.API_KEY", test_key):
        with patch("api.routes.v1.agent.get_agent_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.list_assistants = AsyncMock(return_value=[])
            mock_get_client.return_value = mock_client

            app = create_app()
            client = TestClient(app)

            response = client.get(
                "/api/v1/agent/assistants",
                headers={"Authorization": f"Bearer {test_key}"},
            )
            assert response.status_code == 200


@pytest.mark.asyncio
async def test_missing_api_key_returns_401():
    """Test that missing API key is rejected when required."""
    from unittest.mock import patch

    from fastapi.testclient import TestClient

    from main import create_app

    with patch("config.settings.settings.API_KEY", "test-secret-key"):
        app = create_app()
        client = TestClient(app)

        response = client.get("/api/v1/agent/assistants")
        assert response.status_code == 401
