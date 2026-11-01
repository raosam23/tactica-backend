"""
Shared pytest fixtures for the Tactica test suite.

This module provides reusable fixtures that mock external dependencies:
- Database sessions (AsyncSession)
- Authenticated users
- OpenAI API calls (embeddings and chat completions)
- HTTP clients for testing FastAPI endpoints

All tests run without network access or real API keys.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.user import User


@pytest.fixture
def mock_user() -> User:
    """Create a mock authenticated user for testing."""
    return User(
        id=uuid.uuid4(),
        email="test@example.com",
        password_hash="$2b$12$mockedhashvalue",
        name="Test User",
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_session() -> AsyncMock:
    """
    Create a mock AsyncSession for database operations.

    The mock supports common SQLAlchemy async patterns:
    - execute() returns a result with scalars().all() or scalar_one_or_none()
    - add(), commit(), refresh(), delete() are no-ops
    - get() returns None by default
    """
    session = AsyncMock(spec=AsyncSession)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalars.return_value.first.return_value = None
    mock_result.scalar_one_or_none.return_value = None
    mock_result.all.return_value = []

    session.execute = AsyncMock(return_value=mock_result)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    session.get = AsyncMock(return_value=None)

    return session


@pytest.fixture
def mock_embedding() -> List[float]:
    """Return a deterministic mock embedding vector (1536 dimensions)."""
    return [0.1] * 1536


@pytest.fixture
def mock_openai_embedding_response(mock_embedding: List[float]) -> Dict[str, Any]:
    """Create a mock OpenAI embeddings API response."""
    return {
        "data": [{"embedding": mock_embedding, "index": 0}],
        "model": "text-embedding-3-small",
        "usage": {"prompt_tokens": 10, "total_tokens": 10},
    }


@pytest.fixture
def patch_openai_embeddings(mock_embedding: List[float]):
    """
    Patch the OpenAI embeddings client to return deterministic vectors.

    Use this fixture when testing code that calls generate_embedding() or
    generate_embeddings_batch() from app.services.embedding_service.
    """
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=mock_embedding)]

    with patch("app.services.embedding_service.client") as mock_client:
        mock_client.embeddings.create = AsyncMock(return_value=mock_response)
        yield mock_client


@pytest.fixture
def patch_openai_embeddings_batch(mock_embedding: List[float]):
    """
    Patch the OpenAI embeddings client for batch operations.

    Returns the same embedding for each input text.
    """

    def create_batch_response(texts: List[str]):
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=mock_embedding) for _ in texts]
        return mock_response

    with patch("app.services.embedding_service.client") as mock_client:
        mock_client.embeddings.create = AsyncMock(
            side_effect=lambda input, model: create_batch_response(input)
        )
        yield mock_client


@pytest.fixture
def sample_documents() -> List[Dict[str, Any]]:
    """Sample scraped documents for testing chunking and ingestion."""
    return [
        {
            "title": "Lionel Messi",
            "content": "Lionel Messi is an Argentine professional footballer. " * 50,
            "url": "https://en.wikipedia.org/wiki/Lionel_Messi",
            "source": "wikipedia",
            "sport": "football",
            "tags": ["messi", "football", "argentina"],
        },
        {
            "title": "FC Barcelona",
            "content": "FC Barcelona is a Spanish professional football club. " * 30,
            "url": "https://en.wikipedia.org/wiki/FC_Barcelona",
            "source": "wikipedia",
            "sport": "football",
            "tags": ["barcelona", "football", "spain"],
        },
    ]


@pytest.fixture
def test_client() -> TestClient:
    """Create a synchronous TestClient for FastAPI endpoint testing."""
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing async endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def valid_jwt_token(mock_user: User) -> str:
    """Generate a valid JWT token for the mock user."""
    from app.utils.security import create_access_token

    return create_access_token({"sub": str(mock_user.id)})


@pytest.fixture
def auth_headers(valid_jwt_token: str) -> Dict[str, str]:
    """Return authorization headers with a valid JWT token."""
    return {"Authorization": f"Bearer {valid_jwt_token}"}


@pytest.fixture
def override_get_session(mock_session: AsyncMock):
    """
    Override the get_session dependency to return a mock session.

    Usage:
        def test_something(override_get_session, test_client):
            # test_client will use the mock session
            ...
    """
    from app.db.database import get_session

    async def mock_get_session():
        yield mock_session

    app.dependency_overrides[get_session] = mock_get_session
    yield mock_session
    app.dependency_overrides.clear()


@pytest.fixture
def override_get_current_user(mock_user: User):
    """
    Override the get_current_user dependency to return a mock user.

    Usage:
        def test_protected_endpoint(override_get_current_user, test_client):
            # Requests will be authenticated as mock_user
            ...
    """
    from app.utils.security import get_current_user

    async def mock_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = mock_get_current_user
    yield mock_user
    app.dependency_overrides.clear()


@pytest.fixture
def sample_conversation_id() -> uuid.UUID:
    """Return a deterministic conversation UUID for testing."""
    return uuid.UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture
def sample_message_id() -> uuid.UUID:
    """Return a deterministic message UUID for testing."""
    return uuid.UUID("87654321-4321-8765-4321-876543218765")
