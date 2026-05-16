"""
refresh_token 모델은 localStorage 기반 refresh JWT의 서버 측 세션 상태를 저장한다.
로그아웃과 토큰 재사용 차단을 위해 token_id와 폐기 시각을 관리한다.
"""

from datetime import UTC, datetime

from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field


class RefreshToken(Document):
    """리프레시 토큰 세션 컬렉션의 Beanie 문서 모델이다.

    Args:
        Document: Beanie가 제공하는 MongoDB 문서 기반 클래스.
    """

    user_id: PydanticObjectId
    token_id: Indexed(str, unique=True)
    expires_at: datetime
    revoked_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        """Beanie 컬렉션 설정을 정의한다."""

        name = "refresh_tokens"
