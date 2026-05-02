import uuid
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_200_OK

from app.db.database import get_session
from app.schemas.message import MessageResponse
from app.services.message_service import GetMessagesService
from app.utils.security import get_current_user

router = APIRouter()

@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse], status_code=HTTP_200_OK)
async def get_messages(conversation_id: uuid.UUID, session: AsyncSession = Depends(get_session), user = Depends(get_current_user)) -> List[MessageResponse]:
    """Endpoint to retrieve all messages for a conversation."""
    return await GetMessagesService(session, user, conversation_id)
