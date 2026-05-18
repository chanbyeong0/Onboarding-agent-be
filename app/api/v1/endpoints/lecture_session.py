"""lecture_session 엔드포인트는 강의 세션 생성, 조회, 학습 현황 API를 제공한다."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.api.deps import get_current_admin, get_current_user
from app.crud import chat_message as chat_message_crud
from app.crud import checkpoint as checkpoint_crud
from app.crud import document as document_crud
from app.crud import exam_attempt as exam_attempt_crud
from app.crud import lecture_session as lecture_session_crud
from app.crud import page_explanation as page_explanation_crud
from app.models.exam_attempt import ExamAttempt
from app.models.lecture_session import LectureSession
from app.models.user import User
from app.schemas.chat import ChatRequest
from app.schemas.document import DocumentResponse
from app.schemas.exam import ExamAnswerResult, ExamAttemptResponse, ExamQuestionResponse, ExamSubmitRequest
from app.schemas.lecture_session import (
    LearningSummary,
    LectureSessionCreate,
    LectureSessionList,
    LectureSessionResponse,
)
from app.schemas.page_explanation import PageExplanationRequest, PageExplanationResponse
from app.services import agent_service, tts_service

router = APIRouter(prefix="/lecture-sessions", tags=["lecture-sessions"])


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


def to_exam_response(attempt: ExamAttempt, *, include_answers: bool) -> ExamAttemptResponse:
    """ExamAttempt 문서를 API 응답 스키마로 변환한다."""

    return ExamAttemptResponse(
        id=str(attempt.id),
        session_id=str(attempt.session_id),
        user_id=str(attempt.user_id),
        questions=[
            ExamQuestionResponse(
                question=question.question,
                options=question.options,
                correct_option_index=question.correct_option_index if include_answers else None,
                explanation=question.explanation if include_answers else None,
                source_hint=question.source_hint,
            )
            for question in attempt.questions
        ],
        answers=[
            ExamAnswerResult(
                question_index=answer.question_index,
                selected_option_index=answer.selected_option_index,
                correct_option_index=attempt.questions[answer.question_index].correct_option_index,
                is_correct=answer.is_correct,
            )
            for answer in attempt.answers
            if 0 <= answer.question_index < len(attempt.questions)
        ],
        score=attempt.score,
        created_at=attempt.created_at,
        submitted_at=attempt.submitted_at,
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


@router.post("", response_model=LectureSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    session_in: LectureSessionCreate,
    current_admin: User = Depends(get_current_admin),
) -> LectureSessionResponse:
    """관리자가 강의 세션을 생성한다."""

    for document_id in session_in.document_ids:
        document = await document_crud.get_by_id(document_id)
        if document is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문서를 찾을 수 없습니다.")

    try:
        session = await lecture_session_crud.create(session_in, created_by=str(current_admin.id))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="강의 세션 요청 값이 올바르지 않습니다.") from exc
    return await to_session_response(session)


@router.get("", response_model=LectureSessionList)
async def list_sessions(current_user: User = Depends(get_current_user)) -> LectureSessionList:
    """사용자가 접근 가능한 강의 세션 목록을 조회한다."""

    _ = current_user
    sessions = await lecture_session_crud.list_all()
    return LectureSessionList(sessions=[await to_session_response(session) for session in sessions])


@router.get("/summary", response_model=LearningSummary)
async def get_learning_summary(current_user: User = Depends(get_current_user)) -> LearningSummary:
    """신입 대시보드용 학습 진행률 요약을 반환한다."""

    sessions = await lecture_session_crud.list_all()
    document_ids = {str(document_id) for session in sessions for document_id in session.document_ids}
    checkpoints = await checkpoint_crud.list_by_user(str(current_user.id))
    completed_document_ids = {str(checkpoint.document_id) for checkpoint in checkpoints if str(checkpoint.document_id) in document_ids}
    total_documents = len(document_ids)
    completed_documents = len(completed_document_ids)
    completion_rate = round((completed_documents / total_documents) * 100, 1) if total_documents else 0.0
    question_count = await chat_message_crud.count_by_user(str(current_user.id))

    return LearningSummary(
        total_documents=total_documents,
        completed_documents=completed_documents,
        completion_rate=completion_rate,
        checkpoint_count=len(checkpoints),
        question_count=question_count,
        sessions=[await to_session_response(session) for session in sessions],
    )


@router.post("/{session_id}/explanations", response_model=PageExplanationResponse)
async def create_page_explanation(
    session_id: str,
    explanation_in: PageExplanationRequest,
    current_user: User = Depends(get_current_user),
) -> PageExplanationResponse:
    """강의 페이지 해설 텍스트와 TTS 오디오 URL을 생성하거나 캐시에서 반환한다."""

    session = await lecture_session_crud.get_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="강의 세션을 찾을 수 없습니다.")

    document = await document_crud.get_by_id(explanation_in.document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문서를 찾을 수 없습니다.")
    try:
        document_object_id = PydanticObjectId(explanation_in.document_id)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="문서 ID가 올바르지 않습니다.") from exc
    if document_object_id not in session.document_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="강의 세션에 연결되지 않은 문서입니다.")

    cached = await page_explanation_crud.get_by_scope(
        session_id=session_id,
        document_id=explanation_in.document_id,
        user_id=str(current_user.id),
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
            user_id=str(current_user.id),
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
        user_id=str(current_user.id),
        page_number=explanation_in.page_number,
        text=text,
        audio_path=audio_path,
    )
    audio_url = f"/api/v1/lecture-sessions/{session_id}/explanations/{explanation.id}/audio" if audio_path else None
    return PageExplanationResponse(text=explanation.text, audio_url=audio_url)


@router.post("/{session_id}/exams", response_model=ExamAttemptResponse, status_code=status.HTTP_201_CREATED)
async def create_exam(
    session_id: str,
    current_user: User = Depends(get_current_user),
) -> ExamAttemptResponse:
    """강의 자료와 사용자의 학습 기록을 기반으로 객관식 시험을 생성한다."""

    session = await lecture_session_crud.get_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="강의 세션을 찾을 수 없습니다.")

    checkpoints = await checkpoint_crud.list_by_user_and_session(str(current_user.id), session_id)
    chat_messages = await chat_message_crud.list_by_user_and_session(str(current_user.id), session_id)
    try:
        questions = await agent_service.generate_exam_questions(
            document_ids=[str(document_id) for document_id in session.document_ids],
            checkpoints=[checkpoint.content for checkpoint in checkpoints],
            chat_messages=[
                f"질문: {message.message}\n답변: {message.answer or ''}".strip()
                for message in chat_messages
            ],
        )
    except agent_service.ExamGenerationError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    attempt = await exam_attempt_crud.create(session_id=session_id, user_id=str(current_user.id), questions=questions)
    return to_exam_response(attempt, include_answers=False)


@router.get("/{session_id}/exams/latest", response_model=ExamAttemptResponse | None)
async def get_latest_exam(
    session_id: str,
    current_user: User = Depends(get_current_user),
) -> ExamAttemptResponse | None:
    """사용자의 특정 강의 세션 최신 시험을 조회한다."""

    session = await lecture_session_crud.get_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="강의 세션을 찾을 수 없습니다.")

    attempt = await exam_attempt_crud.get_latest_by_user_and_session(str(current_user.id), session_id)
    if attempt is None:
        return None
    return to_exam_response(attempt, include_answers=attempt.submitted_at is not None)


@router.post("/{session_id}/exams/{exam_id}/submit", response_model=ExamAttemptResponse)
async def submit_exam(
    session_id: str,
    exam_id: str,
    submit_in: ExamSubmitRequest,
    current_user: User = Depends(get_current_user),
) -> ExamAttemptResponse:
    """객관식 시험 답안을 제출하고 서버에 저장된 정답으로 채점한다."""

    attempt = await exam_attempt_crud.get_by_id(exam_id)
    if (
        attempt is None
        or str(attempt.session_id) != session_id
        or str(attempt.user_id) != str(current_user.id)
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="시험을 찾을 수 없습니다.")
    if attempt.submitted_at is not None:
        return to_exam_response(attempt, include_answers=True)

    selected_answers = {answer.question_index: answer.selected_option_index for answer in submit_in.answers}
    if set(selected_answers) != set(range(len(attempt.questions))):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="모든 문항에 답해야 합니다.")
    for question_index, selected_option_index in selected_answers.items():
        if selected_option_index >= len(attempt.questions[question_index].options):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="선택한 보기 번호가 올바르지 않습니다.")

    submitted = await exam_attempt_crud.submit(attempt, selected_answers)
    return to_exam_response(submitted, include_answers=True)


@router.get("/{session_id}/explanations/{explanation_id}/audio")
async def get_page_explanation_audio(
    session_id: str,
    explanation_id: str,
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    """생성된 페이지 해설 TTS 오디오 파일을 반환한다."""

    explanation = await page_explanation_crud.get_by_id(explanation_id)
    if (
        explanation is None
        or str(explanation.session_id) != session_id
        or str(explanation.user_id) != str(current_user.id)
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="해설 오디오를 찾을 수 없습니다.")
    if not explanation.audio_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="해설 오디오가 없습니다.")

    audio_path = Path(explanation.audio_path)
    if not audio_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="해설 오디오 파일을 찾을 수 없습니다.")
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

    session = await lecture_session_crud.get_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="강의 세션을 찾을 수 없습니다.")
    return await to_session_response(session)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    current_admin: User = Depends(get_current_admin),
) -> None:
    """관리자가 강의 세션을 삭제한다."""

    _ = current_admin
    session = await lecture_session_crud.get_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="강의 세션을 찾을 수 없습니다.")

    await checkpoint_crud.delete_by_session(session_id)
    await chat_message_crud.delete_by_session(session_id)
    await page_explanation_crud.delete_by_session(session_id)
    await exam_attempt_crud.delete_by_session(session_id)
    deleted = await lecture_session_crud.delete_by_id(session_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="강의 세션을 찾을 수 없습니다.")
