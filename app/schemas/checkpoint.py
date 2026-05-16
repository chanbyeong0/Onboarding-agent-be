"""
checkpoint 스키마는 사용자가 모르는 항목으로 저장한 내용을 표현한다.
요청에는 문서 id와 페이지 번호, 체크한 텍스트를 포함한다.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CheckpointCreate(BaseModel):
    """체크포인트 생성 요청 스키마다."""

    document_id: str
    session_id: str | None = None
    page_number: int | None = None
    content: str = Field(min_length=1)


class CheckpointResponse(BaseModel):
    """체크포인트 응답 스키마다."""

    id: str
    user_id: str
    document_id: str
    session_id: str | None = None
    page_number: int | None
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
