import uuid
from typing import List, Tuple

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models import Message, MessageCitation, User
from app.models.message import Role as RoleType
from app.models.document import Document
from app.schemas.message import CitationResponse, MessageResponse
from app.services.conversation_service import GetConversationService


async def GetMessagesService(session: AsyncSession, user: User, conversation_id: uuid.UUID) -> List[MessageResponse]:
    """Service to retrieve all messages for a conversation."""
    conversation = await GetConversationService(session, user, conversation_id)
    result = await session.execute(select(Message).where(Message.conversation_id == conversation.id).order_by(Message.created_at.asc()))
    messages = result.scalars().all()
    # return [MessageResponse.model_validate(message) for message in messages]
    message_response = []
    for message in messages:
        citation_result = await session.execute(select(MessageCitation).where(MessageCitation.message_id == message.id))
        message_citations = citation_result.scalars().all()

        citations = []
        if message_citations:
            doc_ids = [citation.document_id for citation in message_citations]
            docs_result = await session.execute(select(Document).where(Document.id.in_(doc_ids)))
            documents = {doc.id: doc for doc in docs_result.scalars().all()}
            for citation in message_citations:
                if citation.document_id in documents:
                    citations.append(
                        CitationResponse(
                            source=f"{documents[citation.document_id].metadata_.get('title', 'Unknown Title')} - {documents[citation.document_id].source}",
                            relevance_score=citation.relevance_score
                        )
                    )
        message_response.append(MessageResponse(
            id=message.id,
            conversation_id=message.conversation_id,
            role=message.role,
            content=message.content,
            created_at=message.created_at,
            citations=citations
        ))
    return message_response
            

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
    return MessageResponse(
        id=new_message.id,
        conversation_id=new_message.conversation_id,
        role=new_message.role,
        content=new_message.content,
        created_at=new_message.created_at,
        citations=[]
    )

async def CreateMessageCitationService(session: AsyncSession, message_id: uuid.UUID, cited_documents: List[Tuple[uuid.UUID, float]]):
    """Service to add cited documents of a message into the database."""
    message = await session.get(Message, message_id)
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    unique_citations: dict[uuid.UUID, float] = {}
    for doc_id, score in cited_documents:
        if doc_id not in unique_citations or score < unique_citations[doc_id]:
            unique_citations[doc_id] = score
    for doc_id, score in unique_citations.items():
        session.add(MessageCitation(
            message_id=message_id,
            document_id=doc_id,
            relevance_score=score
        ))
    await session.commit()
