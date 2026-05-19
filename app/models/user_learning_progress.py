"""user_learning_progress 모델은 사용자별 강의 페이지 열람 진행도를 저장한다."""

from datetime import UTC, datetime

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import IndexModel


class UserLearningProgress(Document):
    """사용자, 강의 세션, 문서 조합별 학습 진행도 문서다."""

    user_id: PydanticObjectId
    session_id: PydanticObjectId
    document_id: PydanticObjectId
    viewed_pages: list[int] = Field(default_factory=list)
    last_page_number: int = 1
    total_pages: int = 0
    study_seconds: int = 0
    completed_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        """Beanie 컬렉션 설정을 정의한다."""

        name = "user_learning_progress"
        indexes = [
            IndexModel(
                [("user_id", 1), ("session_id", 1), ("document_id", 1)],
                unique=True,
                name="uniq_user_session_document_progress",
            ),
            IndexModel([("user_id", 1), ("session_id", 1)], name="idx_user_session_progress"),
        ]
