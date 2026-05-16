"""
document 엔드포인트는 문서 업로드와 문서 메타데이터 조회 API를 제공한다.
업로드된 파일의 파싱과 청크 생성은 서비스 계층에 위임한다.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import get_current_admin, get_current_user
from app.crud import document as document_crud
from app.crud import document_page as document_page_crud
from app.models.document import DocumentModel
from app.models.document_page import DocumentPage
from app.models.user import User
from app.schemas.document import DocumentList, DocumentPageList, DocumentPageResponse, DocumentResponse
from app.services import document_service

router = APIRouter(prefix="/documents", tags=["documents"])


def to_document_response(document: DocumentModel) -> DocumentResponse:
    """DocumentModel 문서를 API 응답 스키마로 변환한다.

    Args:
        document: MongoDB에서 조회한 문서 메타데이터.

    Returns:
        DocumentResponse: 클라이언트에 반환할 문서 응답.
    """

    return DocumentResponse(
        id=str(document.id),
        title=document.title,
        file_path=document.file_path,
        viewer_pdf_url=f"/api/v1/documents/{document.id}/viewer.pdf",
        file_type=document.file_type,
        uploaded_at=document.uploaded_at,
    )


def to_document_page_response(page: DocumentPage) -> DocumentPageResponse:
    """DocumentPage 문서를 API 응답 스키마로 변환한다."""

    return DocumentPageResponse(
        document_id=str(page.document_id),
        page_number=page.page_number,
        image_url=f"/api/v1/documents/{page.document_id}/pages/{page.page_number}/image",
        text=page.text,
    )


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_admin),
) -> DocumentResponse:
    """PDF/PPT 문서를 업로드하고 메타데이터를 저장한다.

    Args:
        file: multipart/form-data로 전달된 업로드 파일.
        current_user: JWT 토큰에서 조회한 현재 사용자.

    Returns:
        DocumentResponse: 저장된 문서 메타데이터.
    """

    _ = current_user

    # 파일 저장, 파싱, 청크 생성을 문서 서비스에 위임한다
    document = await document_service.process_upload(file)
    return to_document_response(document)


@router.get("", response_model=DocumentList)
async def list_documents(current_user: User = Depends(get_current_user)) -> DocumentList:
    """업로드된 문서 목록을 조회한다.

    Args:
        current_user: JWT 토큰에서 조회한 현재 사용자.

    Returns:
        DocumentList: 전체 문서 목록 응답.
    """

    _ = current_user

    # MongoDB에서 문서 메타데이터 목록을 최신순으로 조회한다
    documents = await document_crud.list_all()
    return DocumentList(documents=[to_document_response(document) for document in documents])


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
) -> DocumentResponse:
    """문서 ID로 문서 메타데이터를 조회한다.

    Args:
        document_id: 조회할 문서 ObjectId 문자열.
        current_user: JWT 토큰에서 조회한 현재 사용자.

    Returns:
        DocumentResponse: 문서 상세 응답.

    Raises:
        HTTPException: 문서가 없을 때 발생한다.
    """

    _ = current_user

    # 문서 ObjectId로 MongoDB 문서 메타데이터를 조회한다
    document = await document_crud.get_by_id(document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문서를 찾을 수 없습니다.")
    return to_document_response(document)


@router.get("/{document_id}/viewer.pdf")
async def get_document_viewer_pdf(
    document_id: str,
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    """브라우저 PDF 뷰어가 사용할 PDF 파일을 반환한다."""

    _ = current_user
    document = await document_crud.get_by_id(document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문서를 찾을 수 없습니다.")

    viewer_pdf_path = document.viewer_pdf_path or document.file_path
    pdf_path = Path(viewer_pdf_path)
    if not pdf_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF 뷰어 파일을 찾을 수 없습니다.")
    return FileResponse(pdf_path, media_type="application/pdf")


@router.get("/{document_id}/pages", response_model=DocumentPageList)
async def list_document_pages(
    document_id: str,
    current_user: User = Depends(get_current_user),
) -> DocumentPageList:
    """문서의 페이지 목록과 페이지별 텍스트/이미지 URL을 조회한다."""

    _ = current_user
    document = await document_crud.get_by_id(document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문서를 찾을 수 없습니다.")

    pages = await document_page_crud.list_by_document(document_id)
    return DocumentPageList(pages=[to_document_page_response(page) for page in pages])


@router.get("/{document_id}/pages/{page_number}/image")
async def get_document_page_image(
    document_id: str,
    page_number: int,
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    """문서 페이지 이미지를 반환한다."""

    _ = current_user
    page = await document_page_crud.get_by_document_and_page(document_id, page_number)
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="페이지를 찾을 수 없습니다.")

    image_path = Path(page.image_path)
    if not image_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="페이지 이미지 파일을 찾을 수 없습니다.")
    return FileResponse(image_path, media_type="image/png")
