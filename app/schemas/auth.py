import uuid
from typing import Optional

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    email: str = Field(description="The user's email address")
    password: str = Field(description="The user's password")
    name: Optional[str] = Field(default=None, description="The user's full name")

class LoginRequest(BaseModel):
    email: str = Field(description="The user's email address")
    password: str = Field(description="The user's password")

class TokenResponse(BaseModel):
    access_token: str = Field(description="The JWT access token")
    token_type: str = Field(default="bearer", description="The type of the token")

class DeleteAccountResponse(BaseModel):
    id: uuid.UUID = Field(description="The unique identifier of the deleted user account")
    email: str = Field(description="The email address of the deleted user account")
    name: Optional[str] = Field(default=None, description="The full name of the deleted user account")
