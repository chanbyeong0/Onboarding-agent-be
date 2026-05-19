"""lecture_session 스키마는 강의 세션 생성, 조회, 진행 현황 응답을 정의한다."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.document import DocumentResponse


class LectureSessionCreate(BaseModel):
    """관리자가 강의 세션을 만들 때 사용하는 요청 스키마다."""

    title: str = Field(min_length=1)
    description: str | None = None
    category: str = "개발"
    level: str = "입문"
    document_ids: list[str] = Field(default_factory=list)


class ProgressUpdateRequest(BaseModel):
    """사용자가 열람한 강의 페이지 진행도 갱신 요청이다."""

    document_id: str
    page_number: int = Field(ge=1)
    total_pages: int = Field(ge=1)
    study_seconds_delta: int = Field(default=0, ge=0)


class SessionProgressResponse(BaseModel):
    """강의 세션 단위 사용자 학습 진행도 응답이다."""

    completed_pages: int = 0
    total_pages: int = 0
    progress_rate: float = 0.0
    study_seconds: int = 0
    last_document_id: str | None = None
    last_page_number: int | None = None
    completed_at: datetime | None = None


class LectureSessionResponse(BaseModel):
    """강의 세션 응답 스키마다."""

    id: str
    title: str
    description: str | None
    category: str = "개발"
    level: str = "입문"
    document_ids: list[str]
    documents: list[DocumentResponse] = Field(default_factory=list)
    created_by: str
    created_at: datetime
    progress: SessionProgressResponse | None = None

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
    study_seconds: int = 0
    sessions: list[LectureSessionResponse]
