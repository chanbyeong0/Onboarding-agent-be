"""chat 스키마는 채팅 요청과 응답 페이로드를 정의한다."""

from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """채팅 요청 스키마다."""

    message: str = Field(min_length=1)
    session_id: str | None = None
    document_id: str | None = None
    page_number: int | None = None
    mode: Literal["question", "explain_page"] = "question"
    checkpoints: list[str] = Field(default_factory=list)


class ChatStreamEvent(BaseModel):
    """SSE로 전달할 채팅 스트림 이벤트 스키마다."""

    type: Literal["delta", "done", "error"]
    text: str | None = None
    error: str | None = None


class ChatResponse(BaseModel):
    """일반 JSON 채팅 응답 스키마다."""

    answer: str
