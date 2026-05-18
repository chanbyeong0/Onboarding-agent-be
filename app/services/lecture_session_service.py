"""lecture_session_service 모듈은 강의 세션 관련 비즈니스 흐름을 담당한다."""

import logging
from pathlib import Path

from beanie import PydanticObjectId

from app.crud import chat_message as chat_message_crud
from app.crud import checkpoint as checkpoint_crud
from app.crud import document as document_crud
from app.crud import exam_attempt as exam_attempt_crud
from app.crud import lecture_session as lecture_session_crud
from app.crud import page_explanation as page_explanation_crud
from app.models.lecture_session import LectureSession
from app.schemas.chat import ChatRequest
from app.schemas.document import DocumentResponse
from app.schemas.lecture_session import LearningSummary, LectureSessionCreate, LectureSessionResponse
from app.schemas.page_explanation import PageExplanationRequest, PageExplanationResponse
from app.services import agent_service, tts_service

logger = logging.getLogger(__name__)


class LectureSessionRequestError(RuntimeError):
    """강의 세션 요청 값이 유효하지 않을 때 발생한다."""


async def get_session(session_id: str) -> LectureSession:
    """문자열 ID로 강의 세션을 조회한다."""

    session = await lecture_session_crud.get_by_id(session_id)
    if session is None:
        raise LectureSessionRequestError("강의 세션을 찾을 수 없습니다.")
    return session


async def get_session_response(session_id: str) -> LectureSessionResponse:
    """문자열 ID로 강의 세션을 조회해 응답 스키마로 변환한다."""

    return await to_session_response(await get_session(session_id))


def to_document_response(document) -> DocumentResponse:
    """문서 모델을 강의 세션 응답에 포함할 문서 스키마로 변환한다."""

    return DocumentResponse(
        id=str(document.id),
        title=document.title,
        file_path=document.file_path,
        viewer_pdf_url=f"/api/v1/documents/{document.id}/viewer.pdf",
        file_type=document.file_type,
        uploaded_at=document.uploaded_at,
    )


async def to_session_response(session: LectureSession) -> LectureSessionResponse:
    """LectureSession 문서를 API 응답 스키마로 변환한다."""

    documents = []
    for document_id in session.document_ids:
        document = await document_crud.get_by_id(str(document_id))
        if document is not None:
            documents.append(to_document_response(document))

    return LectureSessionResponse(
        id=str(session.id),
        title=session.title,
        description=session.description,
        document_ids=[str(document_id) for document_id in session.document_ids],
        documents=documents,
        created_by=str(session.created_by),
        created_at=session.created_at,
    )


async def create_session(session_in: LectureSessionCreate, *, created_by: str) -> LectureSessionResponse:
    """문서 존재 여부를 확인한 뒤 강의 세션을 생성한다."""

    for document_id in session_in.document_ids:
        document = await document_crud.get_by_id(document_id)
        if document is None:
            raise LectureSessionRequestError("문서를 찾을 수 없습니다.")
    try:
        session = await lecture_session_crud.create(session_in, created_by=created_by)
    except Exception as exc:
        raise LectureSessionRequestError("강의 세션 요청 값이 올바르지 않습니다.") from exc
    return await to_session_response(session)


async def list_sessions() -> list[LectureSessionResponse]:
    """강의 세션 목록 응답을 조회한다."""

    sessions = await lecture_session_crud.list_all()
    return [await to_session_response(session) for session in sessions]


async def get_learning_summary(user_id: str) -> LearningSummary:
    """신입 대시보드용 학습 진행률 요약을 계산한다."""

    sessions = await lecture_session_crud.list_all()
    document_ids = {str(document_id) for session in sessions for document_id in session.document_ids}
    checkpoints = await checkpoint_crud.list_by_user(user_id)
    completed_document_ids = {str(checkpoint.document_id) for checkpoint in checkpoints if str(checkpoint.document_id) in document_ids}
    total_documents = len(document_ids)
    completed_documents = len(completed_document_ids)
    completion_rate = round((completed_documents / total_documents) * 100, 1) if total_documents else 0.0
    question_count = await chat_message_crud.count_by_user(user_id)

    return LearningSummary(
        total_documents=total_documents,
        completed_documents=completed_documents,
        completion_rate=completion_rate,
        checkpoint_count=len(checkpoints),
        question_count=question_count,
        sessions=[await to_session_response(session) for session in sessions],
    )


async def validate_session_document(session: LectureSession, document_id: str) -> None:
    """해설 대상 문서가 세션에 연결되어 있는지 검증한다."""

    document = await document_crud.get_by_id(document_id)
    if document is None:
        raise LectureSessionRequestError("문서를 찾을 수 없습니다.")
    try:
        document_object_id = PydanticObjectId(document_id)
    except Exception as exc:
        raise LectureSessionRequestError("문서 ID가 올바르지 않습니다.") from exc
    if document_object_id not in session.document_ids:
        raise LectureSessionRequestError("강의 세션에 연결되지 않은 문서입니다.")


async def get_or_create_page_explanation(
    *,
    session: LectureSession,
    session_id: str,
    explanation_in: PageExplanationRequest,
    user_id: str,
) -> PageExplanationResponse:
    """강의 페이지 해설 텍스트와 TTS 오디오를 생성하거나 캐시에서 반환한다."""

    await validate_session_document(session, explanation_in.document_id)
    cached = await page_explanation_crud.get_by_scope(
        session_id=session_id,
        document_id=explanation_in.document_id,
        user_id=user_id,
        page_number=explanation_in.page_number,
    )
    if cached is not None and cached.audio_path:
        return PageExplanationResponse(
            text=cached.text,
            audio_url=f"/api/v1/lecture-sessions/{session_id}/explanations/{cached.id}/audio",
        )

    chat_request = ChatRequest(
        mode="explain_page",
        message=f"{explanation_in.page_number}페이지를 신입에게 설명해주세요.",
        session_id=session_id,
        document_id=explanation_in.document_id,
        page_number=explanation_in.page_number,
        checkpoints=explanation_in.checkpoints,
    )
    text = cached.text if cached is not None else await agent_service.generate_page_explanation(chat_request)
    audio_path = cached.audio_path if cached is not None else None
    try:
        logger.info("TTS 생성 시작: session=%s document=%s page=%s", session_id, explanation_in.document_id, explanation_in.page_number)
        audio_path = await tts_service.synthesize_to_file(
            text=text,
            session_id=session_id,
            document_id=explanation_in.document_id,
            user_id=user_id,
            page_number=explanation_in.page_number,
        )
        logger.info("TTS 생성 완료: %s", audio_path)
    except tts_service.TTSConfigurationError as exc:
        logger.warning("TTS 설정 오류 (API 키 미설정): %s", exc)
        audio_path = None
    except Exception as exc:
        logger.exception("TTS 생성 실패: %s", exc)
        audio_path = None

    explanation = await page_explanation_crud.upsert(
        session_id=session_id,
        document_id=explanation_in.document_id,
        user_id=user_id,
        page_number=explanation_in.page_number,
        text=text,
        audio_path=audio_path,
    )
    audio_url = f"/api/v1/lecture-sessions/{session_id}/explanations/{explanation.id}/audio" if audio_path else None
    return PageExplanationResponse(text=explanation.text, audio_url=audio_url)


async def get_page_explanation_audio_path(*, session_id: str, explanation_id: str, user_id: str) -> Path:
    """생성된 페이지 해설 오디오 파일 경로를 조회하고 검증한다."""

    explanation = await page_explanation_crud.get_by_id(explanation_id)
    if (
        explanation is None
        or str(explanation.session_id) != session_id
        or str(explanation.user_id) != user_id
    ):
        raise LectureSessionRequestError("해설 오디오를 찾을 수 없습니다.")
    if not explanation.audio_path:
        raise LectureSessionRequestError("해설 오디오가 없습니다.")

    audio_path = Path(explanation.audio_path)
    if not audio_path.exists():
        raise LectureSessionRequestError("해설 오디오 파일을 찾을 수 없습니다.")
    return audio_path


async def delete_session_cascade(session_id: str) -> bool:
    """강의 세션과 연결된 학습 데이터를 연쇄 삭제한다."""

    await checkpoint_crud.delete_by_session(session_id)
    await chat_message_crud.delete_by_session(session_id)
    await page_explanation_crud.delete_by_session(session_id)
    await exam_attempt_crud.delete_by_session(session_id)
    return await lecture_session_crud.delete_by_id(session_id)
