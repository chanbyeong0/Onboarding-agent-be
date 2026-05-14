"""
document 스키마는 업로드 문서 메타데이터 응답을 정의한다.
문서 파일 자체는 multipart 업로드로 받고, 스키마는 저장 결과를 표현한다.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    """문서 상세 응답 스키마다."""

    id: str
    title: str
    file_path: str
    file_type: Literal["pdf", "ppt", "pptx"]
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentList(BaseModel):
    """문서 목록 응답 스키마다."""

    documents: list[DocumentResponse]
