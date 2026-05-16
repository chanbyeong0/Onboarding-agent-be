"""
document CRUD 모듈은 업로드 문서 메타데이터의 저장과 조회를 담당한다.
파일 파싱과 청크 생성은 서비스 계층에 맡기고, 이 모듈은 MongoDB 접근만 수행한다.
"""

from beanie import PydanticObjectId

from app.models.document import DocumentModel


async def create(title: str, file_path: str, file_type: str, viewer_pdf_path: str) -> DocumentModel:
    """문서 메타데이터를 저장한다.

    Args:
        title: 사용자가 업로드한 파일명 또는 문서 제목.
        file_path: 서버에 저장된 원본 파일 경로.
        file_type: pdf, ppt, pptx 중 하나.

    Returns:
        DocumentModel: 저장된 문서 문서 모델.
    """

    document = DocumentModel(title=title, file_path=file_path, viewer_pdf_path=viewer_pdf_path, file_type=file_type)

    # Beanie insert로 문서 메타데이터를 documents 컬렉션에 저장한다
    return await document.insert()


async def list_all() -> list[DocumentModel]:
    """전체 문서 목록을 최신순으로 조회한다.

    Returns:
        list[DocumentModel]: 업로드 시각 역순의 문서 목록.
    """

    # 업로드 시각 기준 내림차순으로 문서 목록을 조회한다
    return await DocumentModel.find_all().sort("-uploaded_at").to_list()


async def get_by_id(document_id: str) -> DocumentModel | None:
    """문자열 ObjectId로 문서를 조회한다.

    Args:
        document_id: 문서 ObjectId 문자열.

    Returns:
        DocumentModel | None: 문서가 있으면 모델, 없거나 id가 잘못되면 None.
    """

    try:
        object_id = PydanticObjectId(document_id)
    except Exception:
        return None

    # ObjectId 기본 키로 문서 메타데이터를 조회한다
    return await DocumentModel.get(object_id)
