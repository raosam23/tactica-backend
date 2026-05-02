from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from bcrypt import checkpw, gensalt, hashpw
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.db.database import get_session
from app.models import User

oauth2_scheme = HTTPBearer()

def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return hashpw(password.encode("utf-8"), gensalt(rounds=settings.SALT_ROUNDS)).decode("utf-8")

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a hashed password."""
    return checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))

def create_access_token(data: Dict[str, Any]) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme), session: AsyncSession = Depends(get_session)) -> Optional[User]:
    """Decode the JWT token and return the current user information."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            raise credentials_exception
        result = await session.execute(select(User).where(User.id == user_uuid))
        user = result.scalar_one_or_none()
        if user is None:
            raise credentials_exception
        return user
    except JWTError:
        raise credentials_exception