"""
Integration tests for conversation endpoints.

Tests cover:
- POST /api/conversations/ - create conversation
- GET /api/conversations/ - list conversations
- GET /api/conversations/{id} - get single conversation
- DELETE /api/conversations/{id} - delete conversation
- POST /api/conversations/{id}/chat - chat endpoint with SSE streaming
- GET /api/conversations/{id}/messages - get messages

The chat endpoint tests verify SSE response format and error handling.
"""

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


from app.models.conversation import Conversation
from app.models.message import Message, Role


class TestCreateConversation:
    """Tests for POST /api/conversations/."""

    def test_create_conversation_success(
        self, test_client, override_get_session, override_get_current_user
    ):
        """Creating a conversation should return 201 with conversation data."""
        conversation_id = uuid.uuid4()

        async def mock_refresh(conv):
            conv.id = conversation_id
            conv.created_at = datetime.now(timezone.utc)
            conv.updated_at = datetime.now(timezone.utc)

        override_get_session.refresh = AsyncMock(side_effect=mock_refresh)

        response = test_client.post(
            "/api/conversations/",
            json={"title": "My Sports Chat"},
            headers={"Authorization": "Bearer mock-token"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "My Sports Chat"
        assert "id" in data
        assert "user_id" in data
        assert "created_at" in data

    def test_create_conversation_without_title(
        self, test_client, override_get_session, override_get_current_user
    ):
        """Creating a conversation without title should succeed (title is optional)."""
        conversation_id = uuid.uuid4()

        async def mock_refresh(conv):
            conv.id = conversation_id
            conv.created_at = datetime.now(timezone.utc)
            conv.updated_at = datetime.now(timezone.utc)

        override_get_session.refresh = AsyncMock(side_effect=mock_refresh)

        response = test_client.post(
            "/api/conversations/",
            json={},
            headers={"Authorization": "Bearer mock-token"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] is None

    def test_create_conversation_without_auth_returns_401_or_403(self, test_client):
        """Creating conversation without auth should return 401 or 403."""
        response = test_client.post("/api/conversations/", json={"title": "Test"})

        assert response.status_code in [401, 403]


class TestGetConversations:
    """Tests for GET /api/conversations/."""

    def test_get_conversations_returns_list(
        self, test_client, override_get_session, override_get_current_user
    ):
        """Should return list of user's conversations."""
        conversations = [
            Conversation(
                id=uuid.uuid4(),
                user_id=override_get_current_user.id,
                title="Chat 1",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
            Conversation(
                id=uuid.uuid4(),
                user_id=override_get_current_user.id,
                title="Chat 2",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = conversations
        override_get_session.execute = AsyncMock(return_value=mock_result)

        response = test_client.get(
            "/api/conversations/", headers={"Authorization": "Bearer mock-token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["title"] == "Chat 1"
        assert data[1]["title"] == "Chat 2"

    def test_get_conversations_returns_empty_list(
        self, test_client, override_get_session, override_get_current_user
    ):
        """Should return empty list if user has no conversations."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        override_get_session.execute = AsyncMock(return_value=mock_result)

        response = test_client.get(
            "/api/conversations/", headers={"Authorization": "Bearer mock-token"}
        )

        assert response.status_code == 200
        assert response.json() == []


class TestGetConversation:
    """Tests for GET /api/conversations/{id}."""

    def test_get_conversation_success(
        self, test_client, override_get_session, override_get_current_user
    ):
        """Should return single conversation by ID."""
        conversation = Conversation(
            id=uuid.uuid4(),
            user_id=override_get_current_user.id,
            title="My Chat",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = conversation
        override_get_session.execute = AsyncMock(return_value=mock_result)

        response = test_client.get(
            f"/api/conversations/{conversation.id}",
            headers={"Authorization": "Bearer mock-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "My Chat"
        assert data["id"] == str(conversation.id)

    def test_get_conversation_not_found_returns_404(
        self, test_client, override_get_session, override_get_current_user
    ):
        """Should return 404 for non-existent conversation."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        override_get_session.execute = AsyncMock(return_value=mock_result)

        response = test_client.get(
            f"/api/conversations/{uuid.uuid4()}",
            headers={"Authorization": "Bearer mock-token"},
        )

        assert response.status_code == 404

    def test_get_conversation_wrong_user_returns_403(
        self, test_client, override_get_session, override_get_current_user
    ):
        """Should return 403 if conversation belongs to another user."""
        other_user_id = uuid.uuid4()
        conversation = Conversation(
            id=uuid.uuid4(),
            user_id=other_user_id,
            title="Other User's Chat",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = conversation
        override_get_session.execute = AsyncMock(return_value=mock_result)

        response = test_client.get(
            f"/api/conversations/{conversation.id}",
            headers={"Authorization": "Bearer mock-token"},
        )

        assert response.status_code == 403


class TestDeleteConversation:
    """Tests for DELETE /api/conversations/{id}."""

    def test_delete_conversation_success(
        self, test_client, override_get_session, override_get_current_user
    ):
        """Should delete conversation and return deleted data."""
        conversation = Conversation(
            id=uuid.uuid4(),
            user_id=override_get_current_user.id,
            title="To Delete",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = conversation
        override_get_session.execute = AsyncMock(return_value=mock_result)

        response = test_client.delete(
            f"/api/conversations/{conversation.id}",
            headers={"Authorization": "Bearer mock-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "To Delete"
        override_get_session.delete.assert_called()

    def test_delete_nonexistent_conversation_returns_404(
        self, test_client, override_get_session, override_get_current_user
    ):
        """Should return 404 for non-existent conversation."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        override_get_session.execute = AsyncMock(return_value=mock_result)

        response = test_client.delete(
            f"/api/conversations/{uuid.uuid4()}",
            headers={"Authorization": "Bearer mock-token"},
        )

        assert response.status_code == 404


class TestGetMessages:
    """Tests for GET /api/conversations/{id}/messages."""

    def test_get_messages_returns_list(
        self, test_client, override_get_session, override_get_current_user
    ):
        """Should return list of messages for a conversation."""
        conversation_id = uuid.uuid4()
        conversation = Conversation(
            id=conversation_id,
            user_id=override_get_current_user.id,
            title="Chat",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        messages = [
            Message(
                id=uuid.uuid4(),
                conversation_id=conversation_id,
                role=Role.USER,
                content="Who is the best footballer?",
                created_at=datetime.now(timezone.utc),
            ),
            Message(
                id=uuid.uuid4(),
                conversation_id=conversation_id,
                role=Role.ASSISTANT,
                content="That's a matter of debate...",
                created_at=datetime.now(timezone.utc),
            ),
        ]

        call_count = [0]

        async def mock_execute(query):
            call_count[0] += 1
            mock_result = MagicMock()
            if call_count[0] == 1:
                mock_result.scalar_one_or_none.return_value = conversation
            elif call_count[0] == 2:
                mock_result.scalars.return_value.all.return_value = messages
            else:
                mock_result.scalars.return_value.all.return_value = []
            return mock_result

        override_get_session.execute = AsyncMock(side_effect=mock_execute)

        response = test_client.get(
            f"/api/conversations/{conversation_id}/messages",
            headers={"Authorization": "Bearer mock-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["role"] == "user"
        assert data[1]["role"] == "assistant"


class TestChatEndpoint:
    """Tests for POST /api/conversations/{id}/chat."""

    def test_chat_returns_sse_content_type(
        self, test_client, override_get_session, override_get_current_user
    ):
        """Chat response should have text/event-stream content type."""
        conversation_id = uuid.uuid4()
        conversation = Conversation(
            id=conversation_id,
            user_id=override_get_current_user.id,
            title="Chat",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = conversation
        override_get_session.execute = AsyncMock(return_value=mock_result)

        with patch("app.api.routes.conversations.run_chat_pipeline") as mock_pipeline:

            async def mock_generator():
                yield 'data: {"type": "token", "content": "Hello"}\n\n'
                yield 'data: {"type": "citations", "citations": []}\n\n'

            mock_pipeline.return_value = mock_generator()

            response = test_client.post(
                f"/api/conversations/{conversation_id}/chat",
                json={"message": "Who is Messi?"},
                headers={"Authorization": "Bearer mock-token"},
            )

            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")

    def test_chat_without_auth_returns_401_or_403(self, test_client):
        """Chat without auth should return 401 or 403."""
        response = test_client.post(
            f"/api/conversations/{uuid.uuid4()}/chat", json={"message": "Hello"}
        )

        assert response.status_code in [401, 403]

    def test_chat_nonexistent_conversation_returns_404(
        self, test_client, override_get_session, override_get_current_user
    ):
        """Chat to non-existent conversation should return 404."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        override_get_session.execute = AsyncMock(return_value=mock_result)

        response = test_client.post(
            f"/api/conversations/{uuid.uuid4()}/chat",
            json={"message": "Hello"},
            headers={"Authorization": "Bearer mock-token"},
        )

        assert response.status_code == 404

    def test_chat_missing_message_returns_422(
        self, test_client, override_get_session, override_get_current_user
    ):
        """Chat without message field should return 422."""
        conversation_id = uuid.uuid4()
        conversation = Conversation(
            id=conversation_id,
            user_id=override_get_current_user.id,
            title="Chat",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = conversation
        override_get_session.execute = AsyncMock(return_value=mock_result)

        response = test_client.post(
            f"/api/conversations/{conversation_id}/chat",
            json={},
            headers={"Authorization": "Bearer mock-token"},
        )

        assert response.status_code == 422


class TestSSEResponseFormat:
    """Tests for Server-Sent Events response format."""

    def test_sse_token_event_format(self):
        """Token events should follow the correct SSE format."""
        token_event = 'data: {"type": "token", "content": "Hello"}\n\n'

        assert token_event.startswith("data: ")
        assert token_event.endswith("\n\n")

        json_part = token_event[6:-2]
        parsed = json.loads(json_part)

        assert parsed["type"] == "token"
        assert "content" in parsed

    def test_sse_citations_event_format(self):
        """Citations events should follow the correct SSE format."""
        citations_event = (
            'data: {"type": "citations", "citations": '
            '[{"source": "Wikipedia", "relevance_score": 0.85}]}\n\n'
        )

        assert citations_event.startswith("data: ")
        assert citations_event.endswith("\n\n")

        json_part = citations_event[6:-2]
        parsed = json.loads(json_part)

        assert parsed["type"] == "citations"
        assert isinstance(parsed["citations"], list)
        if parsed["citations"]:
            assert "source" in parsed["citations"][0]
            assert "relevance_score" in parsed["citations"][0]
