"""
user 모델은 온보딩 서비스 사용자의 인증 정보를 MongoDB에 저장한다.
이메일은 로그인 식별자이므로 고유 인덱스로 관리한다.
"""

from datetime import UTC, datetime
from typing import Literal

from beanie import Document, Indexed
from pydantic import Field


class User(Document):
    """사용자 컬렉션 문서 모델이다.

    Args:
        Document: Beanie가 제공하는 MongoDB 문서 기반 클래스.
    """

    email: Indexed(str, unique=True)
    password: str
    name: str
    role: Literal["admin", "trainee"] = "trainee"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        """Beanie 컬렉션 설정을 정의한다."""

        name = "users"
