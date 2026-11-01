"""
Integration tests for authentication endpoints.

Tests cover:
- POST /api/auth/register - user registration
- POST /api/auth/login - user login
- GET /api/auth/me - get current user info
- DELETE /api/auth/me - delete account

All tests mock the database layer to avoid real database connections.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock


from app.models.user import User


class TestRegisterEndpoint:
    """Tests for POST /api/auth/register."""

    def test_register_success_returns_201(self, test_client, override_get_session):
        """Successful registration should return 201 with user data."""
        new_user_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        override_get_session.execute = AsyncMock(return_value=mock_result)

        async def mock_refresh(user):
            user.id = new_user_id
            user.created_at = datetime.now(timezone.utc)

        override_get_session.refresh = AsyncMock(side_effect=mock_refresh)

        response = test_client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "securepassword123",
                "name": "New User",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["name"] == "New User"
        assert "id" in data
        assert "password" not in data
        assert "password_hash" not in data

    def test_register_without_name_succeeds(self, test_client, override_get_session):
        """Registration without name should succeed (name is optional)."""
        new_user_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        override_get_session.execute = AsyncMock(return_value=mock_result)

        async def mock_refresh(user):
            user.id = new_user_id
            user.created_at = datetime.now(timezone.utc)

        override_get_session.refresh = AsyncMock(side_effect=mock_refresh)

        response = test_client.post(
            "/api/auth/register",
            json={"email": "noname@example.com", "password": "securepassword123"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "noname@example.com"
        assert data["name"] is None

    def test_register_duplicate_email_returns_400(
        self, test_client, override_get_session, mock_user
    ):
        """Registering with existing email should return 400."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        override_get_session.execute = AsyncMock(return_value=mock_result)

        response = test_client.post(
            "/api/auth/register",
            json={
                "email": mock_user.email,
                "password": "securepassword123",
                "name": "Another User",
            },
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_register_invalid_email_returns_422(
        self, test_client, override_get_session
    ):
        """Invalid email format should return 422."""
        response = test_client.post(
            "/api/auth/register",
            json={"email": "not-an-email", "password": "securepassword123"},
        )

        assert response.status_code == 422

    def test_register_short_password_returns_422(
        self, test_client, override_get_session
    ):
        """Password shorter than 8 characters should return 422."""
        response = test_client.post(
            "/api/auth/register",
            json={"email": "test@example.com", "password": "short"},
        )

        assert response.status_code == 422

    def test_register_missing_email_returns_422(
        self, test_client, override_get_session
    ):
        """Missing email should return 422."""
        response = test_client.post(
            "/api/auth/register", json={"password": "securepassword123"}
        )

        assert response.status_code == 422

    def test_register_missing_password_returns_422(
        self, test_client, override_get_session
    ):
        """Missing password should return 422."""
        response = test_client.post(
            "/api/auth/register", json={"email": "test@example.com"}
        )

        assert response.status_code == 422


class TestLoginEndpoint:
    """Tests for POST /api/auth/login."""

    def test_login_success_returns_token(self, test_client, override_get_session):
        """Successful login should return JWT token."""
        from app.utils.security import hash_password

        password = "correctpassword"
        user = User(
            id=uuid.uuid4(),
            email="user@example.com",
            password_hash=hash_password(password),
            name="Test User",
            created_at=datetime.now(timezone.utc),
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        override_get_session.execute = AsyncMock(return_value=mock_result)

        response = test_client.post(
            "/api/auth/login", json={"email": user.email, "password": password}
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"].split(".")) == 3

    def test_login_wrong_password_returns_401(self, test_client, override_get_session):
        """Wrong password should return 401."""
        from app.utils.security import hash_password

        user = User(
            id=uuid.uuid4(),
            email="user@example.com",
            password_hash=hash_password("correctpassword"),
            name="Test User",
            created_at=datetime.now(timezone.utc),
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        override_get_session.execute = AsyncMock(return_value=mock_result)

        response = test_client.post(
            "/api/auth/login", json={"email": user.email, "password": "wrongpassword"}
        )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    def test_login_nonexistent_user_returns_401(
        self, test_client, override_get_session
    ):
        """Login with non-existent email should return 401."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        override_get_session.execute = AsyncMock(return_value=mock_result)

        response = test_client.post(
            "/api/auth/login",
            json={"email": "nonexistent@example.com", "password": "anypassword"},
        )

        assert response.status_code == 401

    def test_login_invalid_email_format_returns_422(
        self, test_client, override_get_session
    ):
        """Invalid email format should return 422."""
        response = test_client.post(
            "/api/auth/login", json={"email": "not-an-email", "password": "anypassword"}
        )

        assert response.status_code == 422


class TestGetCurrentUserEndpoint:
    """Tests for GET /api/auth/me."""

    def test_get_me_returns_user_info(self, test_client, override_get_current_user):
        """Authenticated request should return current user info."""
        response = test_client.get(
            "/api/auth/me", headers={"Authorization": "Bearer mock-token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == override_get_current_user.email
        assert data["name"] == override_get_current_user.name
        assert "id" in data

    def test_get_me_without_token_returns_401_or_403(self, test_client):
        """Request without token should return 401 or 403 (implementation dependent)."""
        response = test_client.get("/api/auth/me")

        assert response.status_code in [401, 403]

    def test_get_me_with_invalid_token_returns_401(
        self, test_client, override_get_session
    ):
        """Request with invalid token should return 401."""
        response = test_client.get(
            "/api/auth/me", headers={"Authorization": "Bearer invalid-token"}
        )

        assert response.status_code == 401


class TestDeleteAccountEndpoint:
    """Tests for DELETE /api/auth/me."""

    def test_delete_account_success(
        self, test_client, override_get_session, override_get_current_user
    ):
        """Deleting account should return deleted user info."""
        response = test_client.delete(
            "/api/auth/me", headers={"Authorization": "Bearer mock-token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == override_get_current_user.email

        override_get_session.delete.assert_called_once()
        override_get_session.commit.assert_called()

    def test_delete_account_without_auth_returns_401_or_403(self, test_client):
        """Delete without authentication should return 401 or 403."""
        response = test_client.delete("/api/auth/me")

        assert response.status_code in [401, 403]
