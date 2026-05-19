"""lecture_session 모델은 강의 단위 학습 흐름과 연결 문서를 저장한다."""

from datetime import UTC, datetime

from beanie import Document, PydanticObjectId
from pydantic import Field


class LectureSession(Document):
    """강의 세션 컬렉션의 Beanie 문서 모델이다."""

    title: str
    description: str | None = None
    category: str = "개발"
    level: str = "입문"
    document_ids: list[PydanticObjectId] = Field(default_factory=list)
    created_by: PydanticObjectId
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        """Beanie 컬렉션 설정을 정의한다."""

        name = "lecture_sessions"
