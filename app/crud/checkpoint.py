"""
checkpoint CRUD 모듈은 사용자가 저장한 모르는 항목의 생성과 조회를 담당한다.
사용자별 체크포인트를 빠르게 조회할 수 있도록 user_id 조건으로 필터링한다.
"""

from beanie import PydanticObjectId

from app.models.checkpoint import Checkpoint
from app.schemas.checkpoint import CheckpointCreate


async def create(checkpoint_in: CheckpointCreate, user_id: str) -> Checkpoint:
    """사용자 체크포인트를 생성한다.

    Args:
        checkpoint_in: 문서 id, 페이지 번호, 체크한 내용을 담은 요청.
        user_id: 현재 인증된 사용자 ObjectId 문자열.

    Returns:
        Checkpoint: MongoDB에 저장된 체크포인트 문서.
    """

    checkpoint = Checkpoint(
        user_id=PydanticObjectId(user_id),
        document_id=PydanticObjectId(checkpoint_in.document_id),
        session_id=PydanticObjectId(checkpoint_in.session_id) if checkpoint_in.session_id else None,
        page_number=checkpoint_in.page_number,
        content=checkpoint_in.content,
    )

    # Beanie insert로 체크포인트 문서를 checkpoints 컬렉션에 저장한다
    return await checkpoint.insert()


async def list_by_user(user_id: str) -> list[Checkpoint]:
    """사용자별 체크포인트 목록을 최신순으로 조회한다.

    Args:
        user_id: 현재 인증된 사용자 ObjectId 문자열.

    Returns:
        list[Checkpoint]: 사용자가 저장한 체크포인트 목록.
    """

    object_id = PydanticObjectId(user_id)

    # 사용자 ObjectId로 필터링하고 생성 시각 역순으로 조회한다
    return await Checkpoint.find(Checkpoint.user_id == object_id).sort("-created_at").to_list()


async def list_by_user_and_session(user_id: str, session_id: str) -> list[Checkpoint]:
    """사용자의 특정 강의 세션 체크포인트 목록을 최신순으로 조회한다."""

    return (
        await Checkpoint.find(
            Checkpoint.user_id == PydanticObjectId(user_id),
            Checkpoint.session_id == PydanticObjectId(session_id),
        )
        .sort("-created_at")
        .to_list()
    )


async def count_by_user(user_id: str) -> int:
    """사용자의 전체 체크포인트 수를 계산한다."""

    return await Checkpoint.find(Checkpoint.user_id == PydanticObjectId(user_id)).count()


async def delete_by_session(session_id: str) -> None:
    """삭제된 강의 세션에 연결된 체크포인트를 정리한다."""

    checkpoints = await Checkpoint.find(Checkpoint.session_id == PydanticObjectId(session_id)).to_list()
    for checkpoint in checkpoints:
        await checkpoint.delete()
