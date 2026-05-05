import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ConversationCreate(BaseModel):
    title: Optional[str] = Field(default=None, description="The title of the conversation")

class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID = Field(description="The unique identifier of the conversation")
    user_id: uuid.UUID = Field(description="The unique identifier of the user who owns the conversation")
    title: Optional[str] = Field(default=None, description="The title of the conversation")
    created_at: datetime = Field(description="The timestamp when the conversation was created")
    updated_at: datetime = Field(description="The timestamp when the conversation was last updated")

class ChatRequest(BaseModel):
    message: str = Field(description="The user's message to send to the sports pundit chatbot")

class ChatResponse(BaseModel):
    message: str = Field(description="The sports pundit chatbot's response to the user's message")