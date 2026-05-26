"""SSH 凭据 schemas"""
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field, validator


class SshCredentialCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    username: str = Field(..., min_length=1, max_length=100)
    auth_type: Literal["password", "private_key"]
    password: Optional[str] = None
    private_key: Optional[str] = None
    passphrase: Optional[str] = None

    @validator("name", "username")
    def strip_fields(cls, v):
        return v.strip() if v else v


class SshCredentialUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    username: Optional[str] = Field(None, min_length=1, max_length=100)
    auth_type: Optional[Literal["password", "private_key"]] = None
    password: Optional[str] = None
    private_key: Optional[str] = None
    passphrase: Optional[str] = None


class SshCredentialResponse(BaseModel):
    id: int
    name: str
    username: str
    auth_type: str
    has_password: bool
    has_private_key: bool
    has_passphrase: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
