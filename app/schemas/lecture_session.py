"""lecture_session 스키마는 강의 세션 생성, 조회, 진행 현황 응답을 정의한다."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.document import DocumentResponse


class LectureSessionCreate(BaseModel):
    """관리자가 강의 세션을 만들 때 사용하는 요청 스키마다."""

    title: str = Field(min_length=1)
    description: str | None = None
    document_ids: list[str] = Field(default_factory=list)


class LectureSessionResponse(BaseModel):
    """강의 세션 응답 스키마다."""

    id: str
    title: str
    description: str | None
    document_ids: list[str]
    documents: list[DocumentResponse] = Field(default_factory=list)
    created_by: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LectureSessionList(BaseModel):
    """강의 세션 목록 응답 스키마다."""

    sessions: list[LectureSessionResponse]


class LearningSummary(BaseModel):
    """신입 대시보드 학습 현황 응답 스키마다."""

    total_documents: int
    completed_documents: int
    completion_rate: float
    checkpoint_count: int
    question_count: int
    sessions: list[LectureSessionResponse]
