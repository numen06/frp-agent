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
    sudo_password: Optional[str] = Field(None, max_length=1024)

    @validator("name", "username")
    def strip_fields(cls, v):
        return v.strip() if v else v

    @validator("sudo_password")
    def validate_sudo_password(cls, v):
        if v and ("\n" in v or "\r" in v):
            raise ValueError("sudo 密码不能包含换行符")
        return v


class SshCredentialUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    username: Optional[str] = Field(None, min_length=1, max_length=100)
    auth_type: Optional[Literal["password", "private_key"]] = None
    password: Optional[str] = None
    private_key: Optional[str] = None
    passphrase: Optional[str] = None
    sudo_password: Optional[str] = Field(None, max_length=1024)

    @validator("sudo_password")
    def validate_sudo_password(cls, v):
        if v and ("\n" in v or "\r" in v):
            raise ValueError("sudo 密码不能包含换行符")
        return v


class SshCredentialResponse(BaseModel):
    id: int
    name: str
    username: str
    auth_type: str
    has_password: bool
    has_private_key: bool
    has_passphrase: bool
    has_sudo_password: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
