"""lecture_session CRUD 모듈은 강의 세션 저장과 조회를 담당한다."""

from beanie import PydanticObjectId

from app.models.lecture_session import LectureSession
from app.schemas.lecture_session import LectureSessionCreate


async def create(session_in: LectureSessionCreate, created_by: str) -> LectureSession:
    """관리자가 선택한 문서 목록으로 강의 세션을 생성한다."""

    session = LectureSession(
        title=session_in.title,
        description=session_in.description,
        document_ids=[PydanticObjectId(document_id) for document_id in session_in.document_ids],
        created_by=PydanticObjectId(created_by),
    )
    return await session.insert()


async def list_all() -> list[LectureSession]:
    """전체 강의 세션을 최신순으로 조회한다."""

    return await LectureSession.find_all().sort("-created_at").to_list()


async def get_by_id(session_id: str) -> LectureSession | None:
    """문자열 ObjectId로 강의 세션을 조회한다."""

    try:
        object_id = PydanticObjectId(session_id)
    except Exception:
        return None
    return await LectureSession.get(object_id)


async def delete_by_id(session_id: str) -> bool:
    """문자열 ObjectId로 강의 세션을 삭제한다."""

    session = await get_by_id(session_id)
    if session is None:
        return False
    await session.delete()
    return True
