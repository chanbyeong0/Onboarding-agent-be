"""
user 스키마는 회원가입, 로그인, 사용자 응답 페이로드를 정의한다.
MongoDB ObjectId는 클라이언트가 다루기 쉬운 문자열 id로 노출한다.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


BCRYPT_MAX_PASSWORD_BYTES = 72


def validate_bcrypt_password(value: str) -> str:
    """bcrypt가 처리할 수 있는 비밀번호 바이트 길이를 검증한다."""

    if len(value.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES:
        raise ValueError("비밀번호는 UTF-8 기준 72바이트 이하여야 합니다.")
    return value


class UserCreate(BaseModel):
    """회원가입 요청 스키마다."""

    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(min_length=1)
    role: Literal["trainee"] = "trainee"

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, value: str) -> str:
        """bcrypt 해싱 전에 지원 가능한 비밀번호 길이인지 확인한다."""

        return validate_bcrypt_password(value)


class UserLogin(BaseModel):
    """로그인 요청 스키마다."""

    email: str = Field(min_length=1)
    password: str

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, value: str) -> str:
        """bcrypt 검증 전에 지원 가능한 비밀번호 길이인지 확인한다."""

        return validate_bcrypt_password(value)


class UserResponse(BaseModel):
    """사용자 응답 스키마다."""

    id: str
    email: EmailStr
    name: str
    role: Literal["admin", "trainee"] = "trainee"
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
