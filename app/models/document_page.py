"""document_page 모델은 문서의 페이지별 이미지와 텍스트를 저장한다."""

from beanie import Document, PydanticObjectId


class DocumentPage(Document):
    """문서 페이지 컬렉션의 Beanie 문서 모델이다."""

    document_id: PydanticObjectId
    page_number: int
    image_path: str
    text: str

    class Settings:
        """Beanie 컬렉션 설정을 정의한다."""

        name = "document_pages"
