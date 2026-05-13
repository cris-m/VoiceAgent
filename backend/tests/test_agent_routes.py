from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


class TestThreadOperations:
    @pytest.mark.asyncio
    async def test_create_thread(self, async_client: AsyncClient, authenticated_user):
        with patch("api.routes.v1.agent.get_agent_client") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.create_thread = AsyncMock(return_value={"thread_id": "thread_123", "metadata": {}})
            mock_client.return_value = mock_instance

            response = await async_client.post("/api/v1/agent/threads")
            assert response.status_code == 200
            assert response.json()["thread_id"] == "thread_123"

    @pytest.mark.asyncio
    async def test_create_thread_with_metadata(self, async_client: AsyncClient):
        with patch("api.routes.v1.agent.get_agent_client") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.create_thread = AsyncMock(
                return_value={"thread_id": "thread_456", "metadata": {"name": "My Thread"}}
            )
            mock_client.return_value = mock_instance

            response = await async_client.post("/api/v1/agent/threads", json={"metadata": {"name": "My Thread"}})
            assert response.status_code == 200
            mock_instance.create_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_threads(self, async_client: AsyncClient):
        with patch("api.routes.v1.agent.get_agent_client") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.list_threads = AsyncMock(
                return_value=[{"thread_id": "t1", "metadata": {}}, {"thread_id": "t2", "metadata": {}}]
            )
            mock_client.return_value = mock_instance

            response = await async_client.get("/api/v1/agent/threads")
            assert response.status_code == 200
            assert len(response.json()) == 2

    @pytest.mark.asyncio
    async def test_list_threads_with_pagination(self, async_client: AsyncClient):
        with patch("api.routes.v1.agent.get_agent_client") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.list_threads = AsyncMock(return_value=[])
            mock_client.return_value = mock_instance

            response = await async_client.get("/api/v1/agent/threads?limit=50&offset=10")
            assert response.status_code == 200
            mock_instance.list_threads.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_thread(self, async_client: AsyncClient):
        with patch("api.routes.v1.agent.get_agent_client") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get_thread = AsyncMock(return_value={"thread_id": "thread_789", "metadata": {}})
            mock_client.return_value = mock_instance

            response = await async_client.get("/api/v1/agent/threads/thread_789")
            assert response.status_code == 200
            assert response.json()["thread_id"] == "thread_789"

    @pytest.mark.asyncio
    async def test_get_thread_not_found(self, async_client: AsyncClient):
        with patch("api.routes.v1.agent.get_agent_client") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get_thread = AsyncMock(side_effect=ValueError("Not found"))
            mock_client.return_value = mock_instance

            response = await async_client.get("/api/v1/agent/threads/nonexistent")
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_thread(self, async_client: AsyncClient):
        with patch("api.routes.v1.agent.get_agent_client") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.delete_thread = AsyncMock()
            mock_client.return_value = mock_instance

            response = await async_client.delete("/api/v1/agent/threads/thread_123")
            assert response.status_code == 200
            assert response.json()["status"] == "deleted"

    @pytest.mark.asyncio
    async def test_update_thread_metadata(self, async_client: AsyncClient):
        with patch("api.routes.v1.agent.get_agent_client") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.update_thread_metadata = AsyncMock(
                return_value={"thread_id": "thread_123", "metadata": {"name": "Updated"}}
            )
            mock_client.return_value = mock_instance

            response = await async_client.patch(
                "/api/v1/agent/threads/thread_123/metadata", json={"metadata": {"name": "Updated"}}
            )
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_thread_state(self, async_client: AsyncClient):
        with patch("api.routes.v1.agent.get_agent_client") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get_thread_state = AsyncMock(return_value={"thread_id": "thread_123", "state": {}})
            mock_client.return_value = mock_instance

            response = await async_client.get("/api/v1/agent/threads/thread_123/state")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_thread_history(self, async_client: AsyncClient):
        with patch("api.routes.v1.agent.get_agent_client") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get_run_history = AsyncMock(return_value=[])
            mock_client.return_value = mock_instance

            response = await async_client.get("/api/v1/agent/threads/thread_123/history")
            assert response.status_code == 200


class TestChatOperations:
    @pytest.mark.asyncio
    async def test_chat_requires_authentication(self, async_client: AsyncClient):
        response = await async_client.post("/api/v1/agent/chat", json={"message": "Hello"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_chat_with_auth(self, async_client: AsyncClient, authenticated_user):
        from types import SimpleNamespace

        with patch("api.routes.v1.agent.get_agent_client") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.create_thread = AsyncMock(return_value=SimpleNamespace(thread_id="thread_123"))
            mock_instance.invoke = AsyncMock(return_value="Response")
            mock_client.return_value = mock_instance

            response = await async_client.post(
                "/api/v1/agent/chat",
                json={"message": "Hello"},
                headers={"Authorization": f"Bearer {authenticated_user['token']}"},
            )
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_chat_stream_requires_auth(self, async_client: AsyncClient):
        response = await async_client.post("/api/v1/agent/chat/stream", json={"message": "Hello"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_chat_stream_validates_message(self, async_client: AsyncClient, authenticated_user):
        from fastapi import HTTPException

        with patch("api.routes.v1.agent.safe_chat_message", new_callable=AsyncMock) as mock_validate:
            mock_validate.side_effect = HTTPException(status_code=400, detail="Injection detected")

            response = await async_client.post(
                "/api/v1/agent/chat/stream",
                json={"message": "malicious"},
                headers={"Authorization": f"Bearer {authenticated_user['token']}"},
            )
            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_stream_in_thread_validates_message(self, async_client: AsyncClient, authenticated_user):
        from fastapi import HTTPException

        with patch("api.routes.v1.agent.safe_chat_message", new_callable=AsyncMock) as mock_validate:
            mock_validate.side_effect = HTTPException(status_code=400, detail="Injection detected")

            response = await async_client.post(
                "/api/v1/agent/threads/thread_123/stream?message=malicious",
                headers={"Authorization": f"Bearer {authenticated_user['token']}"},
            )
            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_list_assistants(self, async_client: AsyncClient):
        with patch("api.routes.v1.agent.get_agent_client") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.list_assistants = AsyncMock(
                return_value=[{"assistant_id": "assist_1", "graph_id": "graph_1", "name": "Assistant 1"}]
            )
            mock_client.return_value = mock_instance

            response = await async_client.get("/api/v1/agent/assistants")
            assert response.status_code == 200
            assert len(response.json()) >= 0


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_thread_error_handling(self, async_client: AsyncClient):
        with patch("api.routes.v1.agent.get_agent_client") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get_thread = AsyncMock(side_effect=Exception("Server error"))
            mock_client.return_value = mock_instance

            response = await async_client.get("/api/v1/agent/threads/thread_123")
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_timeout_error_handling(self, async_client: AsyncClient):
        with patch("api.routes.v1.agent.get_agent_client") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.list_assistants = AsyncMock(side_effect=TimeoutError("Request timed out"))
            mock_client.return_value = mock_instance

            response = await async_client.get("/api/v1/agent/assistants")
            assert response.status_code in [500, 504]
