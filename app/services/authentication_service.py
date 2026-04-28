from typing import Optional
from app.models import User
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.security import hash_password, verify_password, create_access_token
from fastapi import HTTPException, status

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