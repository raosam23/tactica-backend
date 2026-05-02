import uuid
from app.models.message import Role as RoleType
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime


class MessageCreate(BaseModel):
    content: str = Field(description="The content of the message")

class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID = Field(description="The unique identifier of the message")
    conversation_id: uuid.UUID = Field(description="The ID of the conversation this message belongs to")
    role: RoleType = Field(description="The role of the message (user or assistant)")
    content: str = Field(description="The content of the message")
    created_at: datetime = Field(description="The timestamp when the message was created")
