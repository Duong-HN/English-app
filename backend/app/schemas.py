from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

AnalysisType = Literal["reading", "writing", "speaking"]


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=2, max_length=120)

    @field_validator("display_name")
    @classmethod
    def clean_display_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("display_name must contain at least 2 non-whitespace characters")
        return cleaned


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    display_name: str
    role: str
    level: str | None
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class AnalysisRequest(BaseModel):
    input_text: str = Field(min_length=3, max_length=10000)

    @field_validator("input_text")
    @classmethod
    def clean_input(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("input_text must contain at least 3 non-whitespace characters")
        return value


class AnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: AnalysisType
    input_text: str
    result: dict
    score: float | None
    provider: str
    created_at: datetime


class HistoryResponse(BaseModel):
    items: list[AnalysisResponse]
    total: int


class MessageResponse(BaseModel):
    message: str
