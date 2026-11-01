"""
Unit tests for RAG service functions.

Tests cover:
- SearchDocumentsService - vector similarity search
- SearchConversationMemoryService - conversation memory search
- AddConversationMemoryService - adding to conversation memory

All tests mock the database and embedding service to be deterministic.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.models.conversation_memory import ConversationMemory
from app.models.document import Document


class TestSearchDocumentsService:
    """Tests for SearchDocumentsService."""

    @pytest.mark.asyncio
    async def test_search_returns_documents_with_scores(
        self, mock_session, mock_embedding
    ):
        """Should return documents ordered by vector similarity."""
        from app.services.rag_service import SearchDocumentsService

        doc1 = Document(
            id=uuid.uuid4(),
            content="Messi scored a hat-trick",
            embedding=mock_embedding,
            source="wikipedia",
            sport="football",
        )
        doc2 = Document(
            id=uuid.uuid4(),
            content="Barcelona won the league",
            embedding=mock_embedding,
            source="espn",
            sport="football",
        )

        mock_result = MagicMock()
        mock_result.all.return_value = [(doc1, 0.15), (doc2, 0.25)]
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.services.rag_service.generate_embedding",
            AsyncMock(return_value=mock_embedding),
        ):
            results = await SearchDocumentsService(
                mock_session, "Messi goals", sport="football", limit=5
            )

        assert len(results) == 2
        assert results[0][0].content == "Messi scored a hat-trick"
        assert results[0][1] == 0.15
        assert results[1][0].content == "Barcelona won the league"

    @pytest.mark.asyncio
    async def test_search_with_sport_filter(self, mock_session, mock_embedding):
        """Should filter results by sport when specified."""
        from app.services.rag_service import SearchDocumentsService

        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.services.rag_service.generate_embedding",
            AsyncMock(return_value=mock_embedding),
        ):
            await SearchDocumentsService(
                mock_session, "player stats", sport="basketball", limit=5
            )

        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_empty_query_raises_400(self, mock_session):
        """Empty query should raise HTTPException with 400 status."""
        from app.services.rag_service import SearchDocumentsService

        with pytest.raises(HTTPException) as exc_info:
            await SearchDocumentsService(mock_session, "   ", limit=5)

        assert exc_info.value.status_code == 400
        assert "empty" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_search_embedding_failure_raises_502(self, mock_session):
        """Embedding service failure should raise HTTPException with 502 status."""
        from app.services.rag_service import SearchDocumentsService

        with patch(
            "app.services.rag_service.generate_embedding",
            AsyncMock(side_effect=Exception("OpenAI error")),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await SearchDocumentsService(mock_session, "valid query", limit=5)

        assert exc_info.value.status_code == 502

    @pytest.mark.asyncio
    async def test_search_returns_empty_list_when_no_matches(
        self, mock_session, mock_embedding
    ):
        """Should return empty list when no documents match."""
        from app.services.rag_service import SearchDocumentsService

        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.services.rag_service.generate_embedding",
            AsyncMock(return_value=mock_embedding),
        ):
            results = await SearchDocumentsService(
                mock_session, "obscure query", limit=5
            )

        assert results == []


class TestSearchConversationMemoryService:
    """Tests for SearchConversationMemoryService."""

    @pytest.mark.asyncio
    async def test_search_memory_returns_memories(self, mock_session, mock_embedding):
        """Should return conversation memories ordered by similarity."""
        from app.services.rag_service import SearchConversationMemoryService

        conversation_id = uuid.uuid4()
        memory1 = ConversationMemory(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            content="User prefers Barcelona over Real Madrid",
            source_type="user_statement",
            embedding=mock_embedding,
        )
        memory2 = ConversationMemory(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            content="Messi is the GOAT according to user",
            source_type="opinion",
            embedding=mock_embedding,
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [memory1, memory2]
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.services.rag_service.generate_embedding",
            AsyncMock(return_value=mock_embedding),
        ):
            results = await SearchConversationMemoryService(
                mock_session, conversation_id, "Barcelona", limit=5
            )

        assert len(results) == 2
        assert results[0].content == "User prefers Barcelona over Real Madrid"

    @pytest.mark.asyncio
    async def test_search_memory_filters_by_conversation_id(
        self, mock_session, mock_embedding
    ):
        """Should only return memories from the specified conversation."""
        from app.services.rag_service import SearchConversationMemoryService

        conversation_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.services.rag_service.generate_embedding",
            AsyncMock(return_value=mock_embedding),
        ):
            await SearchConversationMemoryService(
                mock_session, conversation_id, "query", limit=5
            )

        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_memory_empty_query_raises_400(self, mock_session):
        """Empty query should raise HTTPException with 400 status."""
        from app.services.rag_service import SearchConversationMemoryService

        with pytest.raises(HTTPException) as exc_info:
            await SearchConversationMemoryService(
                mock_session, uuid.uuid4(), "   ", limit=5
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_search_memory_embedding_failure_raises_502(self, mock_session):
        """Embedding failure should raise HTTPException with 502 status."""
        from app.services.rag_service import SearchConversationMemoryService

        with patch(
            "app.services.rag_service.generate_embedding",
            AsyncMock(side_effect=Exception("API error")),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await SearchConversationMemoryService(
                    mock_session, uuid.uuid4(), "valid query", limit=5
                )

        assert exc_info.value.status_code == 502


class TestAddConversationMemoryService:
    """Tests for AddConversationMemoryService."""

    @pytest.mark.asyncio
    async def test_add_memory_success(self, mock_session, mock_embedding):
        """Should successfully add memory to database."""
        from app.services.rag_service import AddConversationMemoryService

        conversation_id = uuid.uuid4()

        with patch(
            "app.services.rag_service.generate_embedding",
            AsyncMock(return_value=mock_embedding),
        ):
            await AddConversationMemoryService(
                mock_session,
                conversation_id,
                content="User likes Messi",
                source_type="user_statement",
                metadata={"confidence": 0.9},
            )

        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_memory_empty_content_raises_400(self, mock_session):
        """Empty content should raise HTTPException with 400 status."""
        from app.services.rag_service import AddConversationMemoryService

        with pytest.raises(HTTPException) as exc_info:
            await AddConversationMemoryService(
                mock_session,
                uuid.uuid4(),
                content="   ",
                source_type="user_statement",
                metadata=None,
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_add_memory_embedding_failure_raises_502(self, mock_session):
        """Embedding failure should raise HTTPException with 502 status."""
        from app.services.rag_service import AddConversationMemoryService

        with patch(
            "app.services.rag_service.generate_embedding",
            AsyncMock(side_effect=Exception("API error")),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await AddConversationMemoryService(
                    mock_session,
                    uuid.uuid4(),
                    content="Some content",
                    source_type="fact",
                    metadata=None,
                )

        assert exc_info.value.status_code == 502

    @pytest.mark.asyncio
    async def test_add_memory_with_various_source_types(
        self, mock_session, mock_embedding
    ):
        """Should accept various valid source_type values."""
        from app.services.rag_service import AddConversationMemoryService

        source_types = ["user_statement", "ai_response", "fact", "opinion", "stat"]

        for source_type in source_types:
            mock_session.execute = AsyncMock()
            mock_session.commit = AsyncMock()

            with patch(
                "app.services.rag_service.generate_embedding",
                AsyncMock(return_value=mock_embedding),
            ):
                await AddConversationMemoryService(
                    mock_session,
                    uuid.uuid4(),
                    content=f"Content for {source_type}",
                    source_type=source_type,
                    metadata=None,
                )

            mock_session.execute.assert_called()

    @pytest.mark.asyncio
    async def test_add_memory_handles_none_metadata(self, mock_session, mock_embedding):
        """Should handle None metadata gracefully."""
        from app.services.rag_service import AddConversationMemoryService

        with patch(
            "app.services.rag_service.generate_embedding",
            AsyncMock(return_value=mock_embedding),
        ):
            await AddConversationMemoryService(
                mock_session,
                uuid.uuid4(),
                content="Some fact",
                source_type="fact",
                metadata=None,
            )

        mock_session.execute.assert_called_once()


class TestRAGToolFunctions:
    """Tests for RAG tool functions used by agents."""

    @pytest.mark.asyncio
    async def test_search_stats_tool_formats_response(
        self, mock_session, mock_embedding
    ):
        """search_stats tool should format results as numbered list."""
        from app.agents.tools import make_tools

        doc = Document(
            id=uuid.uuid4(),
            content="Messi has 800 career goals",
            embedding=mock_embedding,
            source="wikipedia",
            sport="football",
        )

        mock_result = MagicMock()
        mock_result.all.return_value = [(doc, 0.15)]
        mock_session.execute = AsyncMock(return_value=mock_result)

        conversation_id = uuid.uuid4()
        tools, cited_docs = make_tools(mock_session, conversation_id, "football")

        with patch(
            "app.services.rag_service.generate_embedding",
            AsyncMock(return_value=mock_embedding),
        ):
            result = await tools["search_stats"]("Messi goals")

        assert "1." in result
        assert "800 career goals" in result
        assert "wikipedia" in result.lower()
        assert len(cited_docs) == 1

    @pytest.mark.asyncio
    async def test_search_stats_tool_returns_fallback_when_empty(
        self, mock_session, mock_embedding
    ):
        """search_stats should return fallback message when no results."""
        from app.agents.tools import make_tools

        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        conversation_id = uuid.uuid4()
        tools, cited_docs = make_tools(mock_session, conversation_id, "football")

        with patch(
            "app.services.rag_service.generate_embedding",
            AsyncMock(return_value=mock_embedding),
        ):
            result = await tools["search_stats"]("nonexistent topic")

        assert "no relevant" in result.lower()
        assert len(cited_docs) == 0

    @pytest.mark.asyncio
    async def test_cited_documents_list_accumulates(self, mock_session, mock_embedding):
        """cited_documents list should accumulate across multiple searches."""
        from app.agents.tools import make_tools

        doc1 = Document(
            id=uuid.uuid4(),
            content="First result",
            embedding=mock_embedding,
            source="source1",
            sport="football",
        )
        doc2 = Document(
            id=uuid.uuid4(),
            content="Second result",
            embedding=mock_embedding,
            source="source2",
            sport="football",
        )

        call_count = [0]

        def mock_execute_side_effect(*args, **kwargs):
            call_count[0] += 1
            mock_result = MagicMock()
            if call_count[0] == 1:
                mock_result.all.return_value = [(doc1, 0.1)]
            else:
                mock_result.all.return_value = [(doc2, 0.2)]
            return mock_result

        mock_session.execute = AsyncMock(side_effect=mock_execute_side_effect)

        conversation_id = uuid.uuid4()
        tools, cited_docs = make_tools(mock_session, conversation_id, "football")

        with patch(
            "app.services.rag_service.generate_embedding",
            AsyncMock(return_value=mock_embedding),
        ):
            await tools["search_stats"]("query 1")
            await tools["search_articles"]("query 2")

        assert len(cited_docs) == 2
        doc_ids = [doc_id for doc_id, _ in cited_docs]
        assert doc1.id in doc_ids
        assert doc2.id in doc_ids
