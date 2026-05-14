"""
chat 스키마는 SSE 채팅 요청과 스트림 이벤트 페이로드를 정의한다.
응답은 고정 JSON이 아니라 text/event-stream 이벤트로 전송된다.
"""

from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """채팅 요청 스키마다."""

    message: str = Field(min_length=1)
    document_id: str
    page_number: int | None = None
    checkpoints: list[str] = Field(default_factory=list)


class ChatStreamEvent(BaseModel):
    """SSE로 전달할 채팅 스트림 이벤트 스키마다."""

    type: Literal["delta", "done", "error"]
    text: str | None = None
    error: str | None = None
