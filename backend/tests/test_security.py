import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_registration_validation_empty_username(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/auth/register",
        json={"username": "", "email": "test@example.com", "password": "ValidPass123!"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_registration_validation_weak_password(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/auth/register",
        json={"username": "testuser", "email": "test@example.com", "password": "short"},
    )
    assert response.status_code in [422, 400]


@pytest.mark.asyncio
async def test_registration_validation_invalid_email(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/auth/register",
        json={"username": "testuser", "email": "invalid-email", "password": "ValidPass123!"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_error_message_no_enumeration(async_client: AsyncClient):
    response1 = await async_client.post(
        "/api/v1/auth/login", json={"username": "nonexistent_user", "password": "SomePass123!"}
    )
    response2 = await async_client.post(
        "/api/v1/auth/login", json={"username": "nonexistent_user_2", "password": "WrongPass123!"}
    )

    assert response1.status_code == 401
    assert response2.status_code == 401
    assert response1.json()["error"]["message"] == response2.json()["error"]["message"]


@pytest.mark.asyncio
async def test_chat_requires_authentication(async_client: AsyncClient):
    response = await async_client.post("/api/v1/agent/chat", json={"message": "Hello"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_token_rejected(async_client: AsyncClient):
    response = await async_client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_malformed_token_header(async_client: AsyncClient):
    response = await async_client.post("/api/v1/auth/logout", headers={"Authorization": "NotBearer token"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_rate_limit_on_auth_endpoints(async_client: AsyncClient, test_user_data):
    for i in range(15):
        response = await async_client.post(
            "/api/v1/auth/login", json={"username": f"user_{i}", "password": "Password123!"}
        )

        if response.status_code == 429:
            assert "rate limit" in response.json()["error"]["message"].lower()
            break


@pytest.mark.asyncio
async def test_refresh_without_cookie(async_client: AsyncClient):
    response = await async_client.post("/api/v1/auth/refresh")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_with_blacklisted_token(async_client: AsyncClient, test_user_data):
    reg_response = await async_client.post("/api/v1/auth/register", json=test_user_data)
    token = reg_response.json()["access_token"]
    auth_header = {"Authorization": f"Bearer {token}"}

    me_before = await async_client.get("/api/v1/auth/me", headers=auth_header)
    assert me_before.status_code == 200

    logout_resp = await async_client.post("/api/v1/auth/logout", headers=auth_header)
    assert logout_resp.status_code == 200

    me_after = await async_client.get("/api/v1/auth/me", headers=auth_header)
    assert me_after.status_code == 401
