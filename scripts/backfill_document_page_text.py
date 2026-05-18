"""기존 MongoDB 문서 페이지의 빈 텍스트를 원본 파일에서 다시 추출해 채운다."""

import asyncio
from pathlib import Path

from app.crud import document_page as document_page_crud
from app.db.session import close_db, init_db
from app.models.document import DocumentModel
from app.services import document_service


async def backfill_document_page_text() -> None:
    """documents와 document_pages를 순회하며 비어 있는 페이지 텍스트를 업데이트한다."""

    await init_db()
    try:
        documents = await DocumentModel.find_all().to_list()
        updated_count = 0
        skipped_count = 0

        for document in documents:
            file_path = Path(document.file_path)
            if not file_path.exists():
                skipped_count += 1
                print(f"skip missing file: {document.title} ({file_path})")
                continue

            pages = await document_service.extract_pages(file_path, document.file_type)
            text_by_page = {item["page_number"]: str(item.get("text") or "").strip() for item in pages}
            stored_pages = await document_page_crud.list_by_document(str(document.id))

            for page in stored_pages:
                if page.text.strip():
                    continue
                text = text_by_page.get(page.page_number, "")
                if not text:
                    skipped_count += 1
                    print(f"skip empty text: {document.title} page {page.page_number}")
                    continue
                await document_page_crud.update_text(page, text)
                updated_count += 1
                print(f"updated: {document.title} page {page.page_number} ({len(text)} chars)")

        print(f"done: updated={updated_count}, skipped={skipped_count}")
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(backfill_document_page_text())
