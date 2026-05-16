"""page_explanation 스키마는 강의 페이지 해설 요청과 응답을 정의한다."""

from pydantic import BaseModel, Field


class PageExplanationRequest(BaseModel):
    """강의 페이지 해설 생성 요청 스키마다."""

    document_id: str
    page_number: int = Field(ge=1)
    checkpoints: list[str] = Field(default_factory=list)


class PageExplanationResponse(BaseModel):
    """강의 페이지 해설과 TTS 오디오 URL 응답 스키마다."""

    text: str
    audio_url: str | None = None
