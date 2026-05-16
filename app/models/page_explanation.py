"""page_explanation 모델은 강의 페이지별 LLM 해설과 TTS 오디오 경로를 캐시한다."""

from datetime import UTC, datetime

from beanie import Document, PydanticObjectId
from pydantic import Field


class PageExplanation(Document):
    """사용자별 강의 페이지 해설 캐시 모델이다."""

    session_id: PydanticObjectId
    document_id: PydanticObjectId
    user_id: PydanticObjectId
    page_number: int
    text: str
    audio_path: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        """Beanie 컬렉션 설정을 정의한다."""

        name = "page_explanations"
