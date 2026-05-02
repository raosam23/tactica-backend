import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import UUID, Column, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlmodel import Field, Relationship, SQLModel


class Conversation(SQLModel, table=True):
    """Represents a conversation in the database."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(sa_column=Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False))
    title: Optional[str] = Field(default=None)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False
        )
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False
        )
    )
    messages: List["Message"] = Relationship(back_populates="conversation") # type: ignore
    memories: List["ConversationMemory"] = Relationship(back_populates="conversation") # type: ignore