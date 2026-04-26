import uuid
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, ForeignKey, UUID

class MessageCitation(SQLModel, table=True):
    """Represents a citation for a message in the database."""

    __tablename__ = "message_citations"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    message_id: uuid.UUID = Field(sa_column=Column(
        UUID(as_uuid=True),
        ForeignKey("message.id"),
        nullable=False,
    ))
    document_id: uuid.UUID = Field(sa_column=Column(
        UUID(as_uuid=True),
        ForeignKey("document.id"),
        nullable=False,
    ))
    relevance_score: Optional[float] = Field(default=None)
    message: Optional["Message"] = Relationship(back_populates="citations")  # type: ignore
    document: Optional["Document"] = Relationship(back_populates="citations") # type: ignore