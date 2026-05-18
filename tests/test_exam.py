"""test_exam 모듈은 강의 기반 객관식 시험 생성 파싱과 채점을 검증한다."""

import json

import pytest

from app.crud import exam_attempt as exam_attempt_crud
from app.models.exam_attempt import ExamQuestion
from app.services import agent_service


def test_parse_exam_questions_accepts_wrapped_json() -> None:
    """LLM이 반환한 questions 래퍼 JSON을 시험 문항 모델로 변환한다."""

    payload = {
        "questions": [
            {
                "question": f"{index + 1}번 문제",
                "options": ["A", "B", "C", "D"],
                "correct_option_index": index % 4,
                "explanation": "해설",
                "source_hint": "1페이지",
            }
            for index in range(agent_service.EXAM_QUESTION_COUNT)
        ]
    }

    questions = agent_service.parse_exam_questions(json.dumps(payload))

    assert len(questions) == agent_service.EXAM_QUESTION_COUNT
    assert questions[0].options == ["A", "B", "C", "D"]
    assert questions[0].correct_option_index == 0


def test_parse_exam_questions_rejects_bad_option_count() -> None:
    """보기 개수가 맞지 않는 LLM 응답은 거부한다."""

    payload = [
        {
            "question": f"{index + 1}번 문제",
            "options": ["A", "B", "C"],
            "correct_option_index": 0,
            "explanation": "해설",
        }
        for index in range(agent_service.EXAM_QUESTION_COUNT)
    ]

    with pytest.raises(agent_service.ExamGenerationError):
        agent_service.parse_exam_questions(json.dumps(payload))


@pytest.mark.asyncio
async def test_submit_scores_exam_attempt() -> None:
    """제출 답안은 저장된 정답 인덱스로 채점된다."""

    from beanie import PydanticObjectId

    session_id = str(PydanticObjectId())
    user_id = str(PydanticObjectId())
    questions = [
        ExamQuestion(
            question="문제 1",
            options=["A", "B", "C", "D"],
            correct_option_index=1,
            explanation="해설 1",
        ),
        ExamQuestion(
            question="문제 2",
            options=["A", "B", "C", "D"],
            correct_option_index=2,
            explanation="해설 2",
        ),
    ]
    attempt = await exam_attempt_crud.create(session_id=session_id, user_id=user_id, questions=questions)

    submitted = await exam_attempt_crud.submit(attempt, {0: 1, 1: 0})

    assert submitted.score == 50
    assert submitted.answers[0].is_correct is True
    assert submitted.answers[1].is_correct is False
    assert submitted.submitted_at is not None
