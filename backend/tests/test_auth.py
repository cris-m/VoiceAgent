import pytest
from httpx import AsyncClient


class TestRegistration:
    @pytest.mark.asyncio
    async def test_successful_registration(self, async_client: AsyncClient, test_user):
        response = await async_client.post("/api/v1/auth/register", json=test_user)
        assert response.status_code == 201
        data = response.json()
        assert data["access_token"]
        assert data["user_id"]
        assert data["username"] == test_user["username"]
        assert "refresh_token" in response.cookies
        assert response.cookies["refresh_token"]

    @pytest.mark.asyncio
    async def test_registration_returns_all_fields(self, async_client: AsyncClient, test_user):
        response = await async_client.post("/api/v1/auth/register", json=test_user)
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "user_id" in data
        assert "username" in data
        assert "token_type" not in data or data.get("token_type") == "bearer"

    @pytest.mark.asyncio
    async def test_duplicate_username_rejected(self, async_client: AsyncClient, test_user, test_user_2):
        await async_client.post("/api/v1/auth/register", json=test_user)
        duplicate = test_user_2.copy()
        duplicate["username"] = test_user["username"]
        response = await async_client.post("/api/v1/auth/register", json=duplicate)
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_duplicate_email_rejected(self, async_client: AsyncClient, test_user, test_user_2):
        await async_client.post("/api/v1/auth/register", json=test_user)
        duplicate = test_user_2.copy()
        duplicate["email"] = test_user["email"]
        response = await async_client.post("/api/v1/auth/register", json=duplicate)
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_empty_username_rejected(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/auth/register", json={"username": "", "email": "test@example.com", "password": "SecurePass123"}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_email_rejected(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/auth/register", json={"username": "testuser", "email": "not-an-email", "password": "SecurePass123"}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_short_password_rejected(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/auth/register", json={"username": "testuser", "email": "test@example.com", "password": "short"}
        )
        assert response.status_code == 422


class TestLogin:
    @pytest.mark.asyncio
    async def test_successful_login(self, async_client: AsyncClient, test_user):
        await async_client.post("/api/v1/auth/register", json=test_user)
        response = await async_client.post(
            "/api/v1/auth/login", json={"username": test_user["username"], "password": test_user["password"]}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"]
        assert data["user_id"]
        assert "refresh_token" in response.cookies

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, async_client: AsyncClient, test_user):
        await async_client.post("/api/v1/auth/register", json=test_user)
        response = await async_client.post(
            "/api/v1/auth/login", json={"username": test_user["username"], "password": "WrongPassword123"}
        )
        assert response.status_code == 401
        assert "Invalid username or password" in response.json()["error"]["message"]

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/auth/login", json={"username": "nonexistent", "password": "Password123"}
        )
        assert response.status_code == 401
        assert "Invalid username or password" in response.json()["error"]["message"]

    @pytest.mark.asyncio
    async def test_login_missing_username(self, async_client: AsyncClient):
        response = await async_client.post("/api/v1/auth/login", json={"password": "Password123"})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_missing_password(self, async_client: AsyncClient, test_user):
        await async_client.post("/api/v1/auth/register", json=test_user)
        response = await async_client.post("/api/v1/auth/login", json={"username": test_user["username"]})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_error_message_consistency(self, async_client: AsyncClient):
        response1 = await async_client.post("/api/v1/auth/login", json={"username": "user1", "password": "pass1"})
        response2 = await async_client.post("/api/v1/auth/login", json={"username": "user2", "password": "pass2"})
        assert response1.json()["error"]["message"] == response2.json()["error"]["message"]


class TestTokenRefresh:
    @pytest.mark.asyncio
    async def test_successful_refresh(self, async_client: AsyncClient, test_user):
        reg_response = await async_client.post("/api/v1/auth/register", json=test_user)
        old_token = reg_response.json()["access_token"]

        refresh_response = await async_client.post("/api/v1/auth/refresh")
        assert refresh_response.status_code == 200
        new_token = refresh_response.json()["access_token"]

        assert new_token != old_token

    @pytest.mark.asyncio
    async def test_refresh_without_cookie(self, async_client: AsyncClient):
        response = await async_client.post("/api/v1/auth/refresh")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_rotates_token(self, async_client: AsyncClient, test_user):
        await async_client.post("/api/v1/auth/register", json=test_user)

        response1 = await async_client.post("/api/v1/auth/refresh")
        token1 = response1.json()["access_token"]

        response2 = await async_client.post("/api/v1/auth/refresh")
        token2 = response2.json()["access_token"]

        assert token1 != token2

    @pytest.mark.asyncio
    async def test_refresh_returns_user_data(self, async_client: AsyncClient, test_user):
        await async_client.post("/api/v1/auth/register", json=test_user)
        response = await async_client.post("/api/v1/auth/refresh")
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user_id" in data
        assert "username" in data


class TestLogout:
    @pytest.mark.asyncio
    async def test_successful_logout(self, async_client: AsyncClient, test_user):
        reg_response = await async_client.post("/api/v1/auth/register", json=test_user)
        token = reg_response.json()["access_token"]

        response = await async_client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["status"] == "logged out"

    @pytest.mark.asyncio
    async def test_logout_missing_auth_header(self, async_client: AsyncClient):
        response = await async_client.post("/api/v1/auth/logout")
        assert response.status_code == 401
        assert "Missing authorization header" in response.json()["error"]["message"]

    @pytest.mark.asyncio
    async def test_logout_invalid_bearer_format(self, async_client: AsyncClient):
        response = await async_client.post("/api/v1/auth/logout", headers={"Authorization": "InvalidFormat"})
        assert response.status_code == 401
        assert "Invalid authorization header format" in response.json()["error"]["message"]

    @pytest.mark.asyncio
    async def test_logout_invalid_token(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/auth/logout", headers={"Authorization": "Bearer invalid.token.here"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_clears_refresh_cookie(self, async_client: AsyncClient, test_user):
        reg_response = await async_client.post("/api/v1/auth/register", json=test_user)
        token = reg_response.json()["access_token"]

        response = await async_client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["status"] == "logged out"


class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_get_current_user_success(self, async_client: AsyncClient, test_user):
        reg_response = await async_client.post("/api/v1/auth/register", json=test_user)
        token = reg_response.json()["access_token"]
        user_id = reg_response.json()["user_id"]

        response = await async_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == user_id
        assert data["username"] == test_user["username"]
        assert data["email"] == test_user["email"]

    @pytest.mark.asyncio
    async def test_get_current_user_no_token(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/auth/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid"})
        assert response.status_code == 401


class TestAuthFlow:
    @pytest.mark.asyncio
    async def test_full_auth_lifecycle(self, async_client: AsyncClient, test_user):
        reg_response = await async_client.post("/api/v1/auth/register", json=test_user)
        assert reg_response.status_code == 201

        login_response = await async_client.post(
            "/api/v1/auth/login", json={"username": test_user["username"], "password": test_user["password"]}
        )
        assert login_response.status_code == 200

        me_response = await async_client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {login_response.json()['access_token']}"}
        )
        assert me_response.status_code == 200

        logout_response = await async_client.post(
            "/api/v1/auth/logout", headers={"Authorization": f"Bearer {login_response.json()['access_token']}"}
        )
        assert logout_response.status_code == 200

    @pytest.mark.asyncio
    async def test_multiple_users_isolated(self, async_client: AsyncClient, test_user, test_user_2):
        user1_response = await async_client.post("/api/v1/auth/register", json=test_user)
        user1_id = user1_response.json()["user_id"]
        user1_token = user1_response.json()["access_token"]

        user2_response = await async_client.post("/api/v1/auth/register", json=test_user_2)
        user2_id = user2_response.json()["user_id"]
        user2_token = user2_response.json()["access_token"]

        me1_response = await async_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {user1_token}"})
        me2_response = await async_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {user2_token}"})

        assert me1_response.json()["user_id"] == user1_id
        assert me2_response.json()["user_id"] == user2_id
        assert user1_id != user2_id
