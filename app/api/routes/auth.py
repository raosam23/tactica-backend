from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.models import User
from app.schemas.auth import (DeleteAccountResponse, LoginRequest,
                              RegisterRequest, RegisterResponse, TokenResponse)
from app.services.authentication_service import (DeleteAccountService,
                                                 LoginService, RegisterService)
from app.utils.security import get_current_user

router = APIRouter(prefix="/auth")

@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, session: AsyncSession = Depends(get_session)) -> RegisterResponse:
    """Endpoint to handle user registration."""
    return await RegisterService(session, request.email, request.password, request.name)

@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(request: LoginRequest, session: AsyncSession = Depends(get_session)) -> TokenResponse:
    """Endpoint to handle user login."""
    token = await LoginService(session, request.email, request.password)
    return TokenResponse(access_token=token, token_type="bearer")

@router.get("/me", response_model=RegisterResponse, status_code=status.HTTP_200_OK)
async def get_current_user_info(current_user: User = Depends(get_current_user)) -> RegisterResponse:
    """Endpoint to retrieve current user's information."""
    return RegisterResponse.model_validate(current_user)

@router.delete("/me", response_model=DeleteAccountResponse, status_code=status.HTTP_200_OK)
async def delete_account(current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)) -> DeleteAccountResponse:
    """Endpoint to handle account deletion."""
    return await DeleteAccountService(session, current_user)
