from fastapi import APIRouter, Depends, status
from app.services.authentication_service import RegisterService, LoginService, DeleteAccountService
from app.db.database import get_session
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, DeleteAccountResponse
from app.models import User
from app.utils.security import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/auth")

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, session: AsyncSession = Depends(get_session)) -> TokenResponse:
    """Endpoint to handle user registration."""
    token = await RegisterService(session, request.email, request.password, request.name)
    return TokenResponse(access_token=token, token_type="bearer")

@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(request: LoginRequest, session: AsyncSession = Depends(get_session)) -> TokenResponse:
    """Endpoint to handle user login."""
    token = await LoginService(session, request.email, request.password)
    return TokenResponse(access_token=token, token_type="bearer")

@router.delete("/me", response_model=DeleteAccountResponse, status_code=status.HTTP_200_OK)
async def delete_account(current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)) -> DeleteAccountResponse:
    """Endpoint to handle account deletion."""
    return await DeleteAccountService(session, current_user)
