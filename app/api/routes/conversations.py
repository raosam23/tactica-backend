import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.utils.security import get_current_user
from app.db.database import get_session
from app.services.conversation_service import CreateConversationService, GetConversationsService, GetConversationService, DeleteConversationService
from app.schemas.conversation import ConversationCreate, ConversationResponse
from typing import List

router = APIRouter(prefix="/conversations")

@router.post("/", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(conversation: ConversationCreate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)) -> ConversationResponse:
    """Endpoint to create a new conversation."""
    return await CreateConversationService(session, user, conversation)

@router.get("/", response_model=List[ConversationResponse], status_code=status.HTTP_200_OK)
async def get_conversations(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)) -> List[ConversationResponse]:
    """Endpoint to retrieve all conversations for the authenticated user."""
    return await GetConversationsService(session, user)

@router.get("/{conversation_id}", response_model=ConversationResponse, status_code=status.HTTP_200_OK)
async def get_conversation(conversation_id: uuid.UUID, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)) -> ConversationResponse:
    """Endpoint to retrieve a specific conversation by its ID."""
    return await GetConversationService(session, user, conversation_id)

@router.delete("/{conversation_id}", response_model=ConversationResponse, status_code=status.HTTP_200_OK)
async def delete_conversation(conversation_id: uuid.UUID, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)) -> ConversationResponse:
    """Endpoint to delete a specific conversation by its ID."""
    conversation = await GetConversationService(session, user, conversation_id)
    return await DeleteConversationService(session, conversation)
