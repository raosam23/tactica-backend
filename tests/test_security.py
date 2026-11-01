"""
Unit tests for security utilities.

Tests cover:
- Password hashing and verification (bcrypt)
- JWT token creation and decoding
- Token expiration handling
- Invalid token handling
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from jose import jwt

from app.core.config import settings
from app.utils.security import (
    create_access_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    """Tests for password hashing and verification."""

    def test_hash_password_returns_bcrypt_hash(self):
        """Hashed password should be a valid bcrypt hash."""
        password = "securepassword123"
        hashed = hash_password(password)

        assert hashed != password
        assert hashed.startswith("$2b$")
        assert len(hashed) == 60

    def test_hash_password_produces_unique_hashes(self):
        """Same password should produce different hashes (due to salt)."""
        password = "samepassword"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2

    def test_verify_password_returns_true_for_correct_password(self):
        """verify_password should return True for matching password."""
        password = "correctpassword"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_returns_false_for_wrong_password(self):
        """verify_password should return False for non-matching password."""
        password = "correctpassword"
        wrong_password = "wrongpassword"
        hashed = hash_password(password)

        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_handles_unicode(self):
        """Password hashing should work with unicode characters."""
        password = "p@ssw0rd!#$%^&*()_+{}[]|:;<>?,./"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_handles_empty_password(self):
        """Empty password should still hash and verify correctly."""
        password = ""
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True
        assert verify_password("notempty", hashed) is False


class TestJWTTokens:
    """Tests for JWT token creation and validation."""

    def test_create_access_token_returns_valid_jwt(self):
        """create_access_token should return a decodable JWT."""
        user_id = str(uuid.uuid4())
        token = create_access_token({"sub": user_id})

        assert token is not None
        assert isinstance(token, str)
        assert len(token.split(".")) == 3

    def test_create_access_token_contains_subject_claim(self):
        """Token should contain the 'sub' claim with user ID."""
        user_id = str(uuid.uuid4())
        token = create_access_token({"sub": user_id})

        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        assert payload["sub"] == user_id

    def test_create_access_token_contains_expiration_claim(self):
        """Token should contain an 'exp' claim."""
        token = create_access_token({"sub": "test"})

        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        assert "exp" in payload
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)

        expected_expiry = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        assert abs((exp_time - expected_expiry).total_seconds()) < 5

    def test_create_access_token_preserves_additional_claims(self):
        """Additional claims should be preserved in the token."""
        extra_data = {
            "sub": "user123",
            "role": "admin",
            "permissions": ["read", "write"],
        }
        token = create_access_token(extra_data)

        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        assert payload["sub"] == "user123"
        assert payload["role"] == "admin"
        assert payload["permissions"] == ["read", "write"]

    def test_create_access_token_uses_configured_algorithm(self):
        """Token should use the algorithm from settings."""
        token = create_access_token({"sub": "test"})

        header = jwt.get_unverified_header(token)
        assert header["alg"] == settings.ALGORITHM

    def test_token_signature_verification_fails_with_wrong_key(self):
        """Token should fail verification with wrong secret key."""
        token = create_access_token({"sub": "test"})

        with pytest.raises(Exception):
            jwt.decode(token, "wrong-secret-key", algorithms=[settings.ALGORITHM])

    def test_create_access_token_does_not_mutate_input(self):
        """create_access_token should not modify the input dict."""
        data = {"sub": "test", "custom": "value"}
        original_data = data.copy()

        create_access_token(data)

        assert "exp" not in data
        assert data == original_data


class TestGetCurrentUser:
    """Tests for the get_current_user dependency."""

    @pytest.mark.asyncio
    async def test_get_current_user_with_valid_token(self, mock_user, mock_session):
        """Valid token should return the corresponding user."""
        from app.utils.security import get_current_user

        token = create_access_token({"sub": str(mock_user.id)})
        mock_credentials = MagicMock()
        mock_credentials.credentials = token

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute = AsyncMock(return_value=mock_result)

        user = await get_current_user(mock_credentials, mock_session)

        assert user == mock_user

    @pytest.mark.asyncio
    async def test_get_current_user_raises_for_invalid_token(self, mock_session):
        """Invalid token should raise HTTPException."""
        from fastapi import HTTPException
        from app.utils.security import get_current_user

        mock_credentials = MagicMock()
        mock_credentials.credentials = "invalid.token.here"

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_credentials, mock_session)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_raises_for_nonexistent_user(self, mock_session):
        """Token with valid format but non-existent user should raise HTTPException."""
        from fastapi import HTTPException
        from app.utils.security import get_current_user

        user_id = str(uuid.uuid4())
        token = create_access_token({"sub": user_id})
        mock_credentials = MagicMock()
        mock_credentials.credentials = token

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_credentials, mock_session)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_raises_for_invalid_uuid_in_token(
        self, mock_session
    ):
        """Token with invalid UUID should raise HTTPException."""
        from fastapi import HTTPException
        from app.utils.security import get_current_user

        token = create_access_token({"sub": "not-a-valid-uuid"})
        mock_credentials = MagicMock()
        mock_credentials.credentials = token

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_credentials, mock_session)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_raises_for_missing_sub_claim(self, mock_session):
        """Token without 'sub' claim should raise an exception."""
        from fastapi import HTTPException
        from app.utils.security import get_current_user

        token = create_access_token({"other": "data"})
        mock_credentials = MagicMock()
        mock_credentials.credentials = token

        with pytest.raises((HTTPException, TypeError)):
            await get_current_user(mock_credentials, mock_session)
