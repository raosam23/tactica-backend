from fastapi import APIRouter
from app.api.routes import auth_router, conversations_router

api_router = APIRouter(prefix="/api")
api_router.include_router(auth_router, tags=["Authentication"])
api_router.include_router(conversations_router, tags=["Conversations"])