from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models import User
from app.schemas.auth import DeleteAccountResponse
from app.utils.security import (create_access_token, hash_password,
                                verify_password)


async def RegisterService(session: AsyncSession, email: str, password: str, name: Optional[str] = None) -> Optional[str]:
    """Service to handle user registration."""
    result = await session.execute(select(User).where(User.email == email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    password_hash = hash_password(password)
    new_user = User(email=email, password_hash=password_hash, name=name)
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return create_access_token({"sub": str(new_user.id)})

async def LoginService(session: AsyncSession, email: str, password: str) -> Optional[str]:
    """Service to handle user login."""
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return create_access_token({"sub": str(user.id)})

async def DeleteAccountService(session: AsyncSession, user: User) -> DeleteAccountResponse:
    """Service to handle account deletion."""
    await session.delete(user)
    await session.commit()
    return DeleteAccountResponse(id=user.id, email=user.email, name=user.name)
