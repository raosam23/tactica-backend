from pydantic import BaseModel, Field
from typing import Optional

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
