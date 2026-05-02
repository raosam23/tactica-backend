import uuid
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime

class ConversationCreate(BaseModel):
    title: Optional[str] = Field(default=None, description="The title of the conversation")

class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID = Field(description="The unique identifier of the conversation")
    user_id: uuid.UUID = Field(description="The unique identifier of the user who owns the conversation")
    title: Optional[str] = Field(default=None, description="The title of the conversation")
    created_at: datetime = Field(description="The timestamp when the conversation was created")
    updated_at: datetime = Field(description="The timestamp when the conversation was last updated")