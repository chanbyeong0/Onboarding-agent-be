"""
checkpoint 모델은 사용자가 문서에서 모르는 항목으로 표시한 내용을 저장한다.
사용자와 문서 ObjectId를 함께 보관해 개인별 학습 상태를 조회할 수 있게 한다.
"""

from datetime import UTC, datetime

from beanie import Document, PydanticObjectId
from pydantic import Field


class Checkpoint(Document):
    """체크포인트 컬렉션의 Beanie 문서 모델이다.

    Args:
        Document: Beanie가 제공하는 MongoDB 문서 기반 클래스.
    """

    user_id: PydanticObjectId
    document_id: PydanticObjectId
    page_number: int | None = None
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        """Beanie 컬렉션 설정을 정의한다."""

        name = "checkpoints"
