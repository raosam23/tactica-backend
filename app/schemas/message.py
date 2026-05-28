import uuid
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field

from app.models.message import Role as RoleType

class CitationResponse(BaseModel):
    source: str = Field(description="The source of the citation")
    relevance_score: Optional[float] = Field(default=None, description="The relevance score of the citation")

class MessageResponse(BaseModel):
    id: uuid.UUID = Field(description="The unique identifier of the message")
    conversation_id: uuid.UUID = Field(description="The ID of the conversation this message belongs to")
    role: RoleType = Field(description="The role of the message (user or assistant)")
    content: str = Field(description="The content of the message")
    citations: List[CitationResponse] = Field(default_factory=list, description="The list of citations for the message")
    created_at: datetime = Field(description="The timestamp when the message was created")
