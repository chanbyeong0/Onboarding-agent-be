"""exam_service 모듈은 강의 시험 생성, 응답 변환, 제출 검증을 담당한다."""

from app.crud import chat_message as chat_message_crud
from app.crud import checkpoint as checkpoint_crud
from app.crud import exam_attempt as exam_attempt_crud
from app.models.chat_message import ChatMessage
from app.models.exam_attempt import ExamAttempt
from app.models.lecture_session import LectureSession
from app.schemas.exam import ExamAnswerResult, ExamAttemptResponse, ExamQuestionResponse, ExamSubmitRequest
from app.services import agent_service


class ExamSubmissionError(RuntimeError):
    """시험 제출 값이 올바르지 않을 때 발생한다."""


class ExamNotFoundError(RuntimeError):
    """시험 시도를 찾지 못했거나 접근 권한이 없을 때 발생한다."""


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


def format_chat_messages_for_exam(chat_messages: list[ChatMessage]) -> list[str]:
    """시험 생성 프롬프트에 넣을 사용자 질문/답변 기록을 구성한다."""

    return [f"질문: {message.message}\n답변: {message.answer or ''}".strip() for message in chat_messages]


async def create_exam_attempt(*, session: LectureSession, session_id: str, user_id: str) -> ExamAttempt:
    """강의 세션 학습 기록을 바탕으로 시험 시도를 생성한다."""

    checkpoints = await checkpoint_crud.list_by_user_and_session(user_id, session_id)
    chat_messages = await chat_message_crud.list_by_user_and_session(user_id, session_id)
    questions = await agent_service.generate_exam_questions(
        document_ids=[str(document_id) for document_id in session.document_ids],
        checkpoints=[checkpoint.content for checkpoint in checkpoints],
        chat_messages=format_chat_messages_for_exam(chat_messages),
    )
    return await exam_attempt_crud.create(session_id=session_id, user_id=user_id, questions=questions)


async def get_latest_exam_response(*, session_id: str, user_id: str) -> ExamAttemptResponse | None:
    """사용자의 특정 세션 최신 시험 시도 응답을 조회한다."""

    attempt = await exam_attempt_crud.get_latest_by_user_and_session(user_id, session_id)
    if attempt is None:
        return None
    return to_exam_response(attempt, include_answers=attempt.submitted_at is not None)


async def get_owned_attempt(*, exam_id: str, session_id: str, user_id: str) -> ExamAttempt:
    """시험 시도가 현재 사용자와 세션에 속하는지 검증해 반환한다."""

    attempt = await exam_attempt_crud.get_by_id(exam_id)
    if (
        attempt is None
        or str(attempt.session_id) != session_id
        or str(attempt.user_id) != user_id
    ):
        raise ExamNotFoundError("시험을 찾을 수 없습니다.")
    return attempt


def build_selected_answers(submit_in: ExamSubmitRequest, attempt: ExamAttempt) -> dict[int, int]:
    """제출 답안을 dict로 변환하고 문항 수/보기 인덱스를 검증한다."""

    selected_answers = {answer.question_index: answer.selected_option_index for answer in submit_in.answers}
    if set(selected_answers) != set(range(len(attempt.questions))):
        raise ExamSubmissionError("모든 문항에 답해야 합니다.")
    for question_index, selected_option_index in selected_answers.items():
        if selected_option_index >= len(attempt.questions[question_index].options):
            raise ExamSubmissionError("선택한 보기 번호가 올바르지 않습니다.")
    return selected_answers


async def submit_exam_attempt(attempt: ExamAttempt, submit_in: ExamSubmitRequest) -> ExamAttempt:
    """시험 답안을 검증하고 채점 결과를 저장한다."""

    selected_answers = build_selected_answers(submit_in, attempt)
    return await exam_attempt_crud.submit(attempt, selected_answers)
