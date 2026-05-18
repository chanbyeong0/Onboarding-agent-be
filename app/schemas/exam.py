"""exam 스키마는 강의 기반 객관식 시험 생성과 제출 응답을 정의한다."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ExamQuestionResponse(BaseModel):
    """클라이언트에 전달할 시험 문항이다. 정답과 해설은 제출 전에는 숨긴다."""

    question: str
    options: list[str]
    correct_option_index: int | None = None
    explanation: str | None = None
    source_hint: str | None = None


class ExamAnswerSubmit(BaseModel):
    """사용자가 제출하는 단일 문항 답안이다."""

    question_index: int = Field(ge=0)
    selected_option_index: int = Field(ge=0)


class ExamSubmitRequest(BaseModel):
    """시험 제출 요청 스키마다."""

    answers: list[ExamAnswerSubmit]


class ExamAnswerResult(BaseModel):
    """채점된 단일 문항 답안 결과다."""

    question_index: int
    selected_option_index: int
    correct_option_index: int
    is_correct: bool


class ExamAttemptResponse(BaseModel):
    """시험 시도 응답 스키마다."""

    id: str
    session_id: str
    user_id: str
    questions: list[ExamQuestionResponse]
    answers: list[ExamAnswerResult] = Field(default_factory=list)
    score: int | None = None
    created_at: datetime
    submitted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
