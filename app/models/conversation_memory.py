import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import UUID, Column, DateTime, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlmodel import Field, Relationship, SQLModel

from app.core.config import settings


class ConversationMemory(SQLModel, table=True):
    """Conversation-scoped vector memory for retrieval."""

    __tablename__ = "conversation_memory"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    conversation_id: uuid.UUID = Field(
        sa_column=Column(UUID(as_uuid=True), ForeignKey("conversation.id"), nullable=False, index=True)
    )
    content: str = Field(sa_column=Column(Text, nullable=False))
    embedding: Any = Field(sa_column=Column(Vector(settings.VECTOR_DIMENSION), nullable=False))
    source_type: str = Field(sa_column=Column(String, nullable=False, index=True))
    metadata_: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSONB, server_default=text("'{}'::jsonb"), nullable=True),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )

    conversation: Optional["Conversation"] = Relationship(back_populates="memories")  # type: ignore
