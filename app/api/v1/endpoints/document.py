"""
document 엔드포인트는 문서 업로드와 문서 메타데이터 조회 API를 제공한다.
업로드된 파일의 파싱과 청크 생성은 서비스 계층에 위임한다.
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.deps import get_current_user
from app.crud import document as document_crud
from app.models.document import DocumentModel
from app.models.user import User
from app.schemas.document import DocumentList, DocumentResponse
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
        file_type=document.file_type,
        uploaded_at=document.uploaded_at,
    )


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
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
