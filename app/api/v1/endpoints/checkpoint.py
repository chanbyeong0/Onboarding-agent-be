"""
checkpoint 엔드포인트는 사용자가 모르는 항목으로 체크한 내용을 저장하고 조회한다.
모든 체크포인트는 현재 인증된 사용자 기준으로 처리한다.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.crud import checkpoint as checkpoint_crud
from app.crud import document as document_crud
from app.crud import lecture_session as lecture_session_crud
from app.models.checkpoint import Checkpoint
from app.models.user import User
from app.schemas.checkpoint import CheckpointCreate, CheckpointResponse

router = APIRouter(prefix="/checkpoints", tags=["checkpoints"])


def to_checkpoint_response(checkpoint: Checkpoint) -> CheckpointResponse:
    """Checkpoint 문서를 API 응답 스키마로 변환한다.

    Args:
        checkpoint: MongoDB에서 조회한 체크포인트 문서.

    Returns:
        CheckpointResponse: 클라이언트에 반환할 체크포인트 응답.
    """

    return CheckpointResponse(
        id=str(checkpoint.id),
        user_id=str(checkpoint.user_id),
        document_id=str(checkpoint.document_id),
        session_id=str(checkpoint.session_id) if checkpoint.session_id else None,
        page_number=checkpoint.page_number,
        content=checkpoint.content,
        created_at=checkpoint.created_at,
    )


@router.post("", response_model=CheckpointResponse, status_code=status.HTTP_201_CREATED)
async def create_checkpoint(
    checkpoint_in: CheckpointCreate,
    current_user: User = Depends(get_current_user),
) -> CheckpointResponse:
    """현재 사용자의 체크포인트를 저장한다.

    Args:
        checkpoint_in: 체크포인트 생성 요청 데이터.
        current_user: JWT 토큰에서 조회한 현재 사용자.

    Returns:
        CheckpointResponse: 저장된 체크포인트 응답.

    Raises:
        HTTPException: 대상 문서가 없거나 ObjectId가 잘못되었을 때 발생한다.
    """

    # 요청의 문서 ObjectId가 실제 문서에 해당하는지 먼저 확인한다
    document = await document_crud.get_by_id(checkpoint_in.document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문서를 찾을 수 없습니다.")
    if checkpoint_in.session_id:
        session = await lecture_session_crud.get_by_id(checkpoint_in.session_id)
        if session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="강의 세션을 찾을 수 없습니다.")

    try:
        # 현재 사용자 ObjectId와 요청 데이터를 사용해 체크포인트를 저장한다
        checkpoint = await checkpoint_crud.create(checkpoint_in, user_id=str(current_user.id))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="체크포인트 요청 값이 올바르지 않습니다.") from exc
    return to_checkpoint_response(checkpoint)


@router.get("/me", response_model=list[CheckpointResponse])
async def list_my_checkpoints(current_user: User = Depends(get_current_user)) -> list[CheckpointResponse]:
    """현재 사용자의 체크포인트 목록을 조회한다.

    Args:
        current_user: JWT 토큰에서 조회한 현재 사용자.

    Returns:
        list[CheckpointResponse]: 현재 사용자의 체크포인트 목록.
    """

    # 현재 사용자 ObjectId로 MongoDB 체크포인트 목록을 조회한다
    checkpoints = await checkpoint_crud.list_by_user(str(current_user.id))
    return [to_checkpoint_response(checkpoint) for checkpoint in checkpoints]


@router.get("/sessions/{session_id}/me", response_model=list[CheckpointResponse])
async def list_my_session_checkpoints(
    session_id: str,
    current_user: User = Depends(get_current_user),
) -> list[CheckpointResponse]:
    """현재 사용자의 특정 강의 세션 체크포인트 목록을 조회한다."""

    session = await lecture_session_crud.get_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="강의 세션을 찾을 수 없습니다.")

    checkpoints = await checkpoint_crud.list_by_user_and_session(str(current_user.id), session_id)
    return [to_checkpoint_response(checkpoint) for checkpoint in checkpoints]
