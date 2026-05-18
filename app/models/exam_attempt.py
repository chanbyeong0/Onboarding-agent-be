"""exam_attempt 모델은 강의 기반 객관식 시험과 제출 결과를 저장한다."""

from datetime import UTC, datetime

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field


class ExamQuestion(BaseModel):
    """LLM이 생성한 객관식 문항이다."""

    question: str
    options: list[str]
    correct_option_index: int
    explanation: str
    source_hint: str | None = None


class ExamAnswer(BaseModel):
    """사용자가 제출한 단일 문항 답안이다."""

    question_index: int
    selected_option_index: int
    is_correct: bool


class ExamAttempt(Document):
    """강의 세션별 시험 시도 컬렉션의 Beanie 문서 모델이다."""

    session_id: PydanticObjectId
    user_id: PydanticObjectId
    questions: list[ExamQuestion]
    answers: list[ExamAnswer] = Field(default_factory=list)
    score: int | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    submitted_at: datetime | None = None

    class Settings:
        """Beanie 컬렉션 설정을 정의한다."""

        name = "exam_attempts"
