"""chat_message 모델은 강의 세션에서 오간 AI 질문 기록을 저장한다."""

from datetime import UTC, datetime

from beanie import Document, PydanticObjectId
from pydantic import Field


class ChatMessage(Document):
    """강의 세션별 AI 사수 질문/응답 기록 모델이다."""

    session_id: PydanticObjectId
    user_id: PydanticObjectId
    document_id: PydanticObjectId | None = None
    page_number: int | None = None
    message: str
    answer: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        """Beanie 컬렉션 설정을 정의한다."""

        name = "chat_messages"
