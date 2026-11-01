"""
Unit tests for embedding service functions.

Tests cover:
- generate_embedding - single text embedding
- generate_embeddings_batch - batch text embeddings

All tests mock the OpenAI client to avoid API calls.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestGenerateEmbedding:
    """Tests for generate_embedding function."""

    @pytest.mark.asyncio
    async def test_generate_embedding_returns_vector(self, mock_embedding):
        """Should return embedding vector from OpenAI response."""
        from app.services.embedding_service import generate_embedding

        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=mock_embedding)]

        with patch("app.services.embedding_service.client") as mock_client:
            mock_client.embeddings.create = AsyncMock(return_value=mock_response)

            result = await generate_embedding("Test text")

        assert result == mock_embedding
        assert len(result) == 1536

    @pytest.mark.asyncio
    async def test_generate_embedding_calls_openai_with_correct_params(self):
        """Should call OpenAI with correct model and input."""
        from app.services.embedding_service import generate_embedding
        from app.core.config import settings

        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 1536)]

        with patch("app.services.embedding_service.client") as mock_client:
            mock_client.embeddings.create = AsyncMock(return_value=mock_response)

            await generate_embedding("Sample text for embedding")

            mock_client.embeddings.create.assert_called_once_with(
                input="Sample text for embedding", model=settings.EMBEDDING_MODEL
            )

    @pytest.mark.asyncio
    async def test_generate_embedding_raises_on_api_error(self):
        """Should propagate exceptions from OpenAI API."""
        from app.services.embedding_service import generate_embedding

        with patch("app.services.embedding_service.client") as mock_client:
            mock_client.embeddings.create = AsyncMock(
                side_effect=Exception("OpenAI API rate limit exceeded")
            )

            with pytest.raises(Exception) as exc_info:
                await generate_embedding("Test text")

            assert "rate limit" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_generate_embedding_handles_empty_text(self, mock_embedding):
        """Should process empty text without error (OpenAI's decision)."""
        from app.services.embedding_service import generate_embedding

        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=mock_embedding)]

        with patch("app.services.embedding_service.client") as mock_client:
            mock_client.embeddings.create = AsyncMock(return_value=mock_response)

            result = await generate_embedding("")

        assert result == mock_embedding

    @pytest.mark.asyncio
    async def test_generate_embedding_handles_long_text(self, mock_embedding):
        """Should handle long text inputs."""
        from app.services.embedding_service import generate_embedding

        long_text = "A" * 10000

        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=mock_embedding)]

        with patch("app.services.embedding_service.client") as mock_client:
            mock_client.embeddings.create = AsyncMock(return_value=mock_response)

            result = await generate_embedding(long_text)

        assert len(result) == 1536


class TestGenerateEmbeddingsBatch:
    """Tests for generate_embeddings_batch function."""

    @pytest.mark.asyncio
    async def test_batch_returns_embeddings_for_each_text(self, mock_embedding):
        """Should return one embedding per input text."""
        from app.services.embedding_service import generate_embeddings_batch

        texts = ["First text", "Second text", "Third text"]

        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=mock_embedding) for _ in texts]

        with patch("app.services.embedding_service.client") as mock_client:
            mock_client.embeddings.create = AsyncMock(return_value=mock_response)

            results = await generate_embeddings_batch(texts)

        assert len(results) == 3
        for embedding in results:
            assert len(embedding) == 1536

    @pytest.mark.asyncio
    async def test_batch_calls_openai_with_list_input(self, mock_embedding):
        """Should pass texts as a list to OpenAI."""
        from app.services.embedding_service import generate_embeddings_batch
        from app.core.config import settings

        texts = ["Text A", "Text B"]

        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=mock_embedding) for _ in texts]

        with patch("app.services.embedding_service.client") as mock_client:
            mock_client.embeddings.create = AsyncMock(return_value=mock_response)

            await generate_embeddings_batch(texts)

            mock_client.embeddings.create.assert_called_once_with(
                input=texts, model=settings.EMBEDDING_MODEL
            )

    @pytest.mark.asyncio
    async def test_batch_handles_empty_list(self):
        """Should handle empty text list gracefully."""
        from app.services.embedding_service import generate_embeddings_batch

        mock_response = MagicMock()
        mock_response.data = []

        with patch("app.services.embedding_service.client") as mock_client:
            mock_client.embeddings.create = AsyncMock(return_value=mock_response)

            results = await generate_embeddings_batch([])

        assert results == []

    @pytest.mark.asyncio
    async def test_batch_preserves_order(self, mock_embedding):
        """Should preserve order of embeddings matching input texts."""
        from app.services.embedding_service import generate_embeddings_batch

        texts = ["First", "Second", "Third"]

        embeddings = [[0.1] * 1536, [0.2] * 1536, [0.3] * 1536]

        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=emb) for emb in embeddings]

        with patch("app.services.embedding_service.client") as mock_client:
            mock_client.embeddings.create = AsyncMock(return_value=mock_response)

            results = await generate_embeddings_batch(texts)

        assert results[0][0] == 0.1
        assert results[1][0] == 0.2
        assert results[2][0] == 0.3

    @pytest.mark.asyncio
    async def test_batch_raises_on_api_error(self):
        """Should propagate exceptions from OpenAI API."""
        from app.services.embedding_service import generate_embeddings_batch

        with patch("app.services.embedding_service.client") as mock_client:
            mock_client.embeddings.create = AsyncMock(
                side_effect=Exception("API Error")
            )

            with pytest.raises(Exception):
                await generate_embeddings_batch(["text"])

    @pytest.mark.asyncio
    async def test_batch_handles_large_batch(self, mock_embedding):
        """Should handle large batches of texts."""
        from app.services.embedding_service import generate_embeddings_batch

        texts = [f"Text number {i}" for i in range(100)]

        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=mock_embedding) for _ in texts]

        with patch("app.services.embedding_service.client") as mock_client:
            mock_client.embeddings.create = AsyncMock(return_value=mock_response)

            results = await generate_embeddings_batch(texts)

        assert len(results) == 100


class TestEmbeddingDimensions:
    """Tests for embedding dimension consistency."""

    def test_embedding_dimension_matches_config(self):
        """Embedding dimension should match configured vector dimension."""
        from app.core.config import settings

        assert settings.VECTOR_DIMENSION == 1536

    def test_mock_embedding_fixture_has_correct_dimension(self, mock_embedding):
        """Mock embedding fixture should have correct dimension."""
        assert len(mock_embedding) == 1536

    @pytest.mark.asyncio
    async def test_generate_embedding_returns_correct_dimension(self):
        """generate_embedding should return vector with correct dimension."""
        from app.services.embedding_service import generate_embedding
        from app.core.config import settings

        expected_dim = settings.VECTOR_DIMENSION
        mock_vector = [0.1] * expected_dim

        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=mock_vector)]

        with patch("app.services.embedding_service.client") as mock_client:
            mock_client.embeddings.create = AsyncMock(return_value=mock_response)

            result = await generate_embedding("test")

        assert len(result) == expected_dim


class TestEmbeddingModelConfiguration:
    """Tests for embedding model configuration."""

    def test_default_embedding_model(self):
        """Default embedding model should be text-embedding-3-small."""
        from app.core.config import settings

        assert settings.EMBEDDING_MODEL == "text-embedding-3-small"

    @pytest.mark.asyncio
    async def test_uses_configured_model(self):
        """Should use the model specified in settings."""
        from app.services.embedding_service import generate_embedding
        from app.core.config import settings

        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 1536)]

        with patch("app.services.embedding_service.client") as mock_client:
            mock_client.embeddings.create = AsyncMock(return_value=mock_response)

            await generate_embedding("test")

            call_args = mock_client.embeddings.create.call_args
            assert call_args.kwargs["model"] == settings.EMBEDDING_MODEL
