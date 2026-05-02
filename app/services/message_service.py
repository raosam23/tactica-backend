import uuid
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models import Message, User
from app.models.message import Role as RoleType
from app.schemas.message import MessageResponse
from app.services.conversation_service import GetConversationService


async def GetMessagesService(session: AsyncSession, user: User, conversation_id: uuid.UUID) -> List[MessageResponse]:
    """Service to retrieve all messages for a conversation."""
    conversation = await GetConversationService(session, user, conversation_id)
    result = await session.execute(select(Message).where(Message.conversation_id == conversation.id).order_by(Message.created_at.asc()))
    messages = result.scalars().all()
    return [MessageResponse.model_validate(message) for message in messages]

async def CreateMessageService(session: AsyncSession, conversation_id: uuid.UUID, role: RoleType, content: str) -> MessageResponse:
    """Service to create a new message in a conversation."""
    new_message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content
    )
    session.add(new_message)
    await session.commit()
    await session.refresh(new_message)
    return MessageResponse.model_validate(new_message)
