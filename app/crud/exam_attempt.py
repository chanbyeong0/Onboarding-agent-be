"""exam_attempt CRUD 모듈은 강의 기반 시험 시도 저장과 채점을 담당한다."""

from datetime import UTC, datetime

from beanie import PydanticObjectId

from app.models.exam_attempt import ExamAnswer, ExamAttempt, ExamQuestion


async def create(*, session_id: str, user_id: str, questions: list[ExamQuestion]) -> ExamAttempt:
    """사용자의 강의 세션 시험 시도를 생성한다."""

    attempt = ExamAttempt(
        session_id=PydanticObjectId(session_id),
        user_id=PydanticObjectId(user_id),
        questions=questions,
    )
    return await attempt.insert()


async def get_by_id(exam_id: str) -> ExamAttempt | None:
    """시험 시도 ObjectId로 단일 문서를 조회한다."""

    try:
        object_id = PydanticObjectId(exam_id)
    except Exception:
        return None
    return await ExamAttempt.get(object_id)


async def get_latest_by_user_and_session(user_id: str, session_id: str) -> ExamAttempt | None:
    """사용자의 특정 강의 세션 최신 시험 시도를 조회한다."""

    return (
        await ExamAttempt.find(
            ExamAttempt.user_id == PydanticObjectId(user_id),
            ExamAttempt.session_id == PydanticObjectId(session_id),
        )
        .sort("-created_at")
        .first_or_none()
    )


async def submit(attempt: ExamAttempt, selected_answers: dict[int, int]) -> ExamAttempt:
    """제출 답안을 채점하고 시험 시도 문서에 저장한다."""

    answers: list[ExamAnswer] = []
    correct_count = 0
    for question_index, question in enumerate(attempt.questions):
        selected_option_index = selected_answers.get(question_index, -1)
        is_correct = selected_option_index == question.correct_option_index
        if is_correct:
            correct_count += 1
        answers.append(
            ExamAnswer(
                question_index=question_index,
                selected_option_index=selected_option_index,
                is_correct=is_correct,
            )
        )

    attempt.answers = answers
    attempt.score = round((correct_count / len(attempt.questions)) * 100) if attempt.questions else 0
    attempt.submitted_at = datetime.now(UTC)
    return await attempt.save()


async def delete_by_session(session_id: str) -> None:
    """삭제된 강의 세션에 연결된 시험 시도를 정리한다."""

    attempts = await ExamAttempt.find(ExamAttempt.session_id == PydanticObjectId(session_id)).to_list()
    for attempt in attempts:
        await attempt.delete()
