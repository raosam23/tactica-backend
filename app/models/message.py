import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import UUID, Column, DateTime, ForeignKey
from sqlalchemy.sql import func

class Role(str, Enum):
    """Defines the role of a message in a conversation."""
    USER = "user"
    ASSISTANT = "assistant"

class Message(SQLModel, table=True):
    """Represents a message in the database."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    conversation_id: uuid.UUID = Field(sa_column=Column(UUID(as_uuid=True), ForeignKey("conversation.id"), nullable=False))
    role: Role = Field(nullable=False)
    content: str = Field(nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False
        )
    )
    conversation: Optional["Conversation"] = Relationship(back_populates="messages") # type: ignore
    citations: List["MessageCitation"] = Relationship(back_populates="message") # type: ignore
