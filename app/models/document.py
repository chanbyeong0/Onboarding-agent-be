"""
document 모델은 업로드된 PDF/PPT 파일의 메타데이터를 저장한다.
원본 파일 경로와 문서 유형을 기준으로 후속 파싱과 RAG 색인을 연결한다.
"""

from datetime import UTC, datetime
from typing import Literal

from beanie import Document
from pydantic import Field


class DocumentModel(Document):
    """업로드 문서 컬렉션의 Beanie 문서 모델이다.

    Args:
        Document: Beanie가 제공하는 MongoDB 문서 기반 클래스.
    """

    title: str
    file_path: str
    viewer_pdf_path: str | None = None
    file_type: Literal["pdf", "ppt", "pptx"]
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        """Beanie 컬렉션 설정을 정의한다."""

        name = "documents"
