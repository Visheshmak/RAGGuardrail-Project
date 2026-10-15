from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from typing import Optional
from uuid import UUID
from datetime import datetime
from app.models.user import UserRole
from app.core.security import validate_password_length

class UserBase(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

    @field_validator("password")
    @classmethod
    def validate_password(cls, password: str) -> str:
        return validate_password_length(password)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, password: str) -> str:
        return validate_password_length(password)

class UserResponse(UserBase):
    id: UUID
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
