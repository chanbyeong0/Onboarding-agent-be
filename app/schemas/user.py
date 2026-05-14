"""
user 스키마는 회원가입, 로그인, 사용자 응답 페이로드를 정의한다.
MongoDB ObjectId는 클라이언트가 다루기 쉬운 문자열 id로 노출한다.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """회원가입 요청 스키마다."""

    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(min_length=1)


class UserLogin(BaseModel):
    """로그인 요청 스키마다."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """사용자 응답 스키마다."""

    id: str
    email: EmailStr
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """JWT 로그인 응답 스키마다."""

    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """액세스 토큰 재발급 요청 스키마다."""

    refresh_token: str


class LogoutRequest(BaseModel):
    """로그아웃 요청 스키마다."""

    refresh_token: str | None = None
