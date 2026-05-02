import uuid
from app.schemas.conversation import ConversationCreate, ConversationResponse
from app.models import Conversation, User
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from typing import List

async def CreateConversationService(session: AsyncSession, user: User, conversation: ConversationCreate) -> ConversationResponse:
    """Service to create a new conversation."""
    new_conversation = Conversation(user_id=user.id, title=conversation.title)
    session.add(new_conversation)
    await session.commit()
    await session.refresh(new_conversation)
    return new_conversation

async def GetConversationsService(session: AsyncSession, user: User) -> List[ConversationResponse]:
    """Service to retrieve all conversations for a user."""
    result = await session.execute(select(Conversation).where(Conversation.user_id == user.id).order_by(Conversation.updated_at.desc()))
    conversations = result.scalars().all()
    return conversations

async def GetConversationService(session: AsyncSession, user: User, conversation_id: uuid.UUID) -> ConversationResponse:
    """Service to retrieve a specific conversation by ID."""
    result = await session.execute(select(Conversation).where(Conversation.id == conversation_id))
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    if conversation.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to access this conversation.")
    return conversation

async def DeleteConversationService(session: AsyncSession, conversation: Conversation) -> ConversationResponse:
    """Service to delete a conversation."""
    await session.delete(conversation)
    await session.commit()
    return conversation
