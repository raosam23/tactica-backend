import uuid
from typing import Optional, List, Any, Dict
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import ARRAY, Text, Column, DateTime, String, text
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
from datetime import datetime, timezone
from app.core.config import settings

class Document(SQLModel, table=True):
    """Represents a document in the database."""
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    content: str = Field(sa_column=Column(Text, nullable=False))
    embedding: Any = Field(sa_column=Column(Vector(settings.VECTOR_DIMENSION)))
    source: str = Field(index=True)
    sport: Optional[str] = Field(default=None, index=True)
    tags: Optional[List[str]] = Field(default_factory=list, sa_column=Column(ARRAY(String), server_default=text("'{}'::text[]")))
    metadata_: Optional[Dict[str, Any]] = Field(default_factory=dict, sa_column=Column("metadata", JSONB, server_default=text("'{}'::jsonb")))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False
        )
    )
    citations: List["MessageCitation"] = Relationship(back_populates="document") # type: ignore