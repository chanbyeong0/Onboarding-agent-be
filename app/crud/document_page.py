"""document_page CRUD 모듈은 문서 페이지 생성과 조회를 담당한다."""

from beanie import PydanticObjectId

from app.models.document_page import DocumentPage


async def create_many(document_id: str, pages: list[dict[str, object]]) -> list[DocumentPage]:
    """문서 페이지 목록을 저장한다."""

    document_object_id = PydanticObjectId(document_id)
    page_documents = [
        DocumentPage(
            document_id=document_object_id,
            page_number=int(page["page_number"]),
            image_path=str(page["image_path"]),
            text=str(page.get("text") or ""),
        )
        for page in pages
    ]
    if not page_documents:
        return []
    await DocumentPage.insert_many(page_documents)
    return page_documents


async def list_by_document(document_id: str) -> list[DocumentPage]:
    """문서에 속한 페이지 목록을 페이지 번호순으로 조회한다."""

    return (
        await DocumentPage.find(DocumentPage.document_id == PydanticObjectId(document_id))
        .sort("page_number")
        .to_list()
    )


async def get_by_document_and_page(document_id: str, page_number: int) -> DocumentPage | None:
    """문서 ID와 페이지 번호로 단일 페이지를 조회한다."""

    return await DocumentPage.find_one(
        DocumentPage.document_id == PydanticObjectId(document_id),
        DocumentPage.page_number == page_number,
    )
