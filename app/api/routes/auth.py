from fastapi import APIRouter, Depends
from app.services.authentication_service import RegisterService, LoginService
from app.db.database import get_session
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/auth")

@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest, session: AsyncSession = Depends(get_session)) -> TokenResponse:
    """Endpoint to handle user registration."""
    token = await RegisterService(session, request.email, request.password, request.name)
    return TokenResponse(access_token=token, token_type="bearer")

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, session: AsyncSession = Depends(get_session)) -> TokenResponse:
    """Endpoint to handle user login."""
    token = await LoginService(session, request.email, request.password)
    return TokenResponse(access_token=token, token_type="bearer")