import uuid
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models import ConversationMemory, Document
from app.services.embedding_service import generate_embedding


async def SearchDocumentsService(session: AsyncSession, query: str, sport: Optional[str] = None, limit: int = 5) -> List[Document]:
    """
    Search for documents based on a query and optional sport filter.
    
    Args:
        session (AsyncSession): The database session to use for the search.
        query (str): The search query string.
        sport (Optional[str]): An optional filter for the sport type.
        limit (int): The maximum number of results to return.
    Returns:
        List[Document]: A list of documents matching the search criteria.
    """
    if not query.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Query cannot be empty")
    try:
        embeddings: List[float] = await generate_embedding(query)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Failed to generate embeddings: {str(e)}")
    statement = (
        select(Document)
        .order_by(Document.embedding.cosine_distance(embeddings))
        .limit(limit)
    )
    if sport:
        statement = statement.where(Document.sport == sport)
    try:
        results = await session.execute(statement)
    except SQLAlchemyError as err:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(err)}")
    return results.scalars().all()

async def SearchConversationMemoryService(session: AsyncSession, conversation_id: uuid.UUID, query: str, limit: int = 5) -> List[ConversationMemory]:
    """
    Search for conversation memory based on a query.
    
    Args:
        session (AsyncSession): The database session to use for the search.
        conversation_id (uuid.UUID): The ID of the conversation to search within.
        query (str): The search query string.
        limit (int): The maximum number of results to return.
    Returns:
        List[ConversationMemory]: A list of conversation memory entries matching the search criteria.
    """
    if not query.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Query cannot be empty")
    try:
        embeddings: List[float] = await generate_embedding(query)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Failed to generate embeddings: {str(e)}")
    statement = (
        select(ConversationMemory)
        .where(ConversationMemory.conversation_id == conversation_id)
        .order_by(ConversationMemory.embedding.cosine_distance(embeddings))
        .limit(limit)
    )
    try:
        results = await session.execute(statement)
    except SQLAlchemyError as err:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(err)}")
    return results.scalars().all()

async def AddConversationMemoryService(session: AsyncSession, conversation_id: uuid.UUID, content: str, source_type: str, metadata: Optional[Dict[Any, Any]]) -> ConversationMemory:
    """
    Add a new entry to the conversation memory.
    
    Args:
        session (AsyncSession): The database session to use for adding memory.
        conversation_id (uuid.UUID): The ID of the conversation to which the memory belongs.
        content (str): The content of the memory entry.
        source_type (str): The source type of the memory entry (e.g., user_statement, ai_response, fact, story, etc.).
        metadata (Optional[Dict[Any, Any]]): Additional metadata for the memory entry.
    Returns:
        ConversationMemory: The newly created conversation memory entry.    
    """
    if not content.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Content cannot be empty")
    try:
        embeddings = await generate_embedding(content)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Failed to generate embeddings: {str(e)}")
    memory_entry = ConversationMemory(
        conversation_id=conversation_id,
        content=content,
        source_type=source_type,
        metadata_=metadata,
        embedding=embeddings
    )
    session.add(memory_entry)
    try:
        await session.commit()
        await session.refresh(memory_entry)
    except SQLAlchemyError as err:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(err)}")
    return memory_entry
