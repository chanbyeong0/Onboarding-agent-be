"""lecture_session 엔드포인트는 강의 세션 생성, 조회, 학습 현황 API를 제공한다."""

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.api.deps import get_current_admin, get_current_user
from app.models.user import User
from app.schemas.exam import ExamAttemptResponse, ExamSubmitRequest
from app.schemas.lecture_session import (
    LearningSummary,
    LectureSessionCreate,
    LectureSessionList,
    LectureSessionResponse,
    ProgressUpdateRequest,
    SessionProgressResponse,
)
from app.schemas.page_explanation import PageExplanationRequest, PageExplanationResponse
from app.services import agent_service, exam_service, lecture_session_service

router = APIRouter(prefix="/lecture-sessions", tags=["lecture-sessions"])


@router.post("", response_model=LectureSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    session_in: LectureSessionCreate,
    current_admin: User = Depends(get_current_admin),
) -> LectureSessionResponse:
    """관리자가 강의 세션을 생성한다."""

    try:
        return await lecture_session_service.create_session(session_in, created_by=str(current_admin.id))
    except lecture_session_service.LectureSessionRequestError as exc:
        detail = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if detail == "문서를 찾을 수 없습니다." else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=detail) from exc


@router.get("", response_model=LectureSessionList)
async def list_sessions(current_user: User = Depends(get_current_user)) -> LectureSessionList:
    """사용자가 접근 가능한 강의 세션 목록을 조회한다."""

    _ = current_user
    return LectureSessionList(sessions=await lecture_session_service.list_sessions())


@router.get("/summary", response_model=LearningSummary)
async def get_learning_summary(current_user: User = Depends(get_current_user)) -> LearningSummary:
    """신입 대시보드용 학습 진행률 요약을 반환한다."""

    return await lecture_session_service.get_learning_summary(str(current_user.id))


@router.patch("/{session_id}/progress", response_model=SessionProgressResponse)
async def update_learning_progress(
    session_id: str,
    progress_in: ProgressUpdateRequest,
    current_user: User = Depends(get_current_user),
) -> SessionProgressResponse:
    """사용자의 특정 강의 세션 페이지 열람 진행도를 갱신한다."""

    try:
        PydanticObjectId(session_id)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="강의 세션 ID가 올바르지 않습니다.") from exc

    try:
        return await lecture_session_service.update_learning_progress(
            session_id=session_id,
            user_id=str(current_user.id),
            progress_in=progress_in,
        )
    except lecture_session_service.LectureSessionRequestError as exc:
        detail = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if "찾을 수 없습니다" in detail else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=detail) from exc


@router.post("/{session_id}/explanations", response_model=PageExplanationResponse)
async def create_page_explanation(
    session_id: str,
    explanation_in: PageExplanationRequest,
    current_user: User = Depends(get_current_user),
) -> PageExplanationResponse:
    """강의 페이지 해설 텍스트와 TTS 오디오 URL을 생성하거나 캐시에서 반환한다."""

    try:
        session = await lecture_session_service.get_session(session_id)
        return await lecture_session_service.get_or_create_page_explanation(
            session=session,
            session_id=session_id,
            explanation_in=explanation_in,
            user_id=str(current_user.id),
        )
    except lecture_session_service.LectureSessionRequestError as exc:
        detail = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if "찾을 수 없습니다" in detail else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=detail) from exc


@router.post("/{session_id}/exams", response_model=ExamAttemptResponse, status_code=status.HTTP_201_CREATED)
async def create_exam(
    session_id: str,
    current_user: User = Depends(get_current_user),
) -> ExamAttemptResponse:
    """강의 자료와 사용자의 학습 기록을 기반으로 객관식 시험을 생성한다."""

    try:
        session = await lecture_session_service.get_session(session_id)
        attempt = await exam_service.create_exam_attempt(
            session=session,
            session_id=session_id,
            user_id=str(current_user.id),
        )
        return exam_service.to_exam_response(attempt, include_answers=False)
    except lecture_session_service.LectureSessionRequestError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except agent_service.ExamGenerationError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get("/{session_id}/exams/latest", response_model=ExamAttemptResponse | None)
async def get_latest_exam(
    session_id: str,
    current_user: User = Depends(get_current_user),
) -> ExamAttemptResponse | None:
    """사용자의 특정 강의 세션 최신 시험을 조회한다."""

    try:
        await lecture_session_service.get_session(session_id)
    except lecture_session_service.LectureSessionRequestError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return await exam_service.get_latest_exam_response(session_id=session_id, user_id=str(current_user.id))


@router.post("/{session_id}/exams/{exam_id}/submit", response_model=ExamAttemptResponse)
async def submit_exam(
    session_id: str,
    exam_id: str,
    submit_in: ExamSubmitRequest,
    current_user: User = Depends(get_current_user),
) -> ExamAttemptResponse:
    """객관식 시험 답안을 제출하고 서버에 저장된 정답으로 채점한다."""

    try:
        attempt = await exam_service.get_owned_attempt(
            exam_id=exam_id,
            session_id=session_id,
            user_id=str(current_user.id),
        )
    except exam_service.ExamNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if attempt.submitted_at is not None:
        return exam_service.to_exam_response(attempt, include_answers=True)

    try:
        submitted = await exam_service.submit_exam_attempt(attempt, submit_in)
    except exam_service.ExamSubmissionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return exam_service.to_exam_response(submitted, include_answers=True)


@router.get("/{session_id}/explanations/{explanation_id}/audio")
async def get_page_explanation_audio(
    session_id: str,
    explanation_id: str,
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    """생성된 페이지 해설 TTS 오디오 파일을 반환한다."""

    try:
        audio_path = await lecture_session_service.get_page_explanation_audio_path(
            session_id=session_id,
            explanation_id=explanation_id,
            user_id=str(current_user.id),
        )
    except lecture_session_service.LectureSessionRequestError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return FileResponse(audio_path, media_type="audio/mpeg")


@router.get("/{session_id}", response_model=LectureSessionResponse)
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
) -> LectureSessionResponse:
    """강의 세션 상세 정보를 조회한다."""

    _ = current_user
    try:
        PydanticObjectId(session_id)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="강의 세션 ID가 올바르지 않습니다.") from exc

    try:
        return await lecture_session_service.get_session_response(session_id, user_id=str(current_user.id))
    except lecture_session_service.LectureSessionRequestError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    current_admin: User = Depends(get_current_admin),
) -> None:
    """관리자가 강의 세션을 삭제한다."""

    _ = current_admin
    try:
        await lecture_session_service.get_session(session_id)
    except lecture_session_service.LectureSessionRequestError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    deleted = await lecture_session_service.delete_session_cascade(session_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="강의 세션을 찾을 수 없습니다.")
