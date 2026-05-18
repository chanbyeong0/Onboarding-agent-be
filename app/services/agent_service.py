"""
agent_service 모듈은 OpenAI Chat Completions 스트리밍을 사용해
사용자 질문에 대한 토큰 단위 응답을 생성하고 SSE로 전달할 수 있도록 한다.
RAG 컨텍스트 주입 지점은 TODO로 표시되어 있다.
"""

import asyncio
import json
from collections.abc import AsyncIterator
from pathlib import Path

from pydantic import ValidationError
from openai import APIError, AsyncOpenAI

from app.crud import document as document_crud
from app.crud import document_page as document_page_crud
from app.core.config import settings
from app.models.exam_attempt import ExamQuestion
from app.schemas.chat import ChatRequest, ChatStreamEvent
from app.services import document_service

SYSTEM_PROMPT = """
당신은 사내 신입사원 온보딩을 돕는 친절한 AI 사수입니다.
항상 따뜻하고 격려하는 말투로 대화하세요. 신입사원이 편하게 질문할 수 있도록 친근한 어조를 유지하세요.
사용자의 질문 의도에 맞는 길이로 답하세요.
짧은 인사, 감사, 확인 같은 말에는 1~2문장으로 짧게 응답하고 슬라이드 내용을 임의로 요약하지 마세요.
일반 질문에는 3~6문장으로 먼저 답하고, 필요한 경우 예시나 단계 목록을 덧붙이세요.
문서 컨텍스트가 부족하면 모르는 내용을 지어내지 말고 추가 자료 확인이 필요하다고 말하세요.
요청 유형이 explain_page일 때는 현재 페이지를 신입 교육용으로 충분히 설명하세요.
explain_page 답변 구성: 먼저 이 페이지에서 가장 중요한 핵심을 한두 문장으로 짚어주고, 주요 개념이나 내용을 친절하게 풀어서 설명한 뒤, 실무에서 어떻게 활용되는지 알려주세요. 마지막에는 꼭 기억할 포인트를 한두 가지로 정리해주세요.
현재 페이지에 명령어, 코드, 설정 파일, URL, 옵션 플래그가 있으면 원문과 역할, 주요 옵션/인자, 주의할 점을 짧게 설명하세요.
""".strip()

SHORT_REPLY_MESSAGES = {
    "안녕",
    "안녕하세요",
    "하이",
    "hello",
    "hi",
    "네",
    "예",
    "응",
    "고마워",
    "감사합니다",
    "오케이",
    "ok",
}

EXAM_QUESTION_COUNT = 5
EXAM_OPTION_COUNT = 4
MAX_EXAM_CONTEXT_CHARS = 12000


class ExamGenerationError(RuntimeError):
    """LLM 시험 문항 생성 결과가 유효하지 않을 때 발생한다."""


def get_openai_client() -> AsyncOpenAI:
    """OpenAI 비동기 클라이언트를 생성한다.

    Returns:
        AsyncOpenAI: Chat Completions 스트리밍에 사용할 비동기 클라이언트.
    """

    base_url = settings.openai_base_url
    # 빈 문자열이나 None은 무시하고 기본 OpenAI 엔드포인트를 사용한다
    valid_base_url = base_url if base_url and base_url.startswith(("http://", "https://")) else None
    return AsyncOpenAI(api_key=settings.openai_api_key, base_url=valid_base_url)


def build_user_prompt(request: ChatRequest, context: list[str]) -> str:
    """요청과 컨텍스트를 OpenAI 사용자 메시지로 합성한다.

    Args:
        request: 채팅 요청. message/document_id/page_number/checkpoints 포함.
        context: RAG로 조회한 문서 컨텍스트 목록.

    Returns:
        str: 모델에 전달할 사용자 메시지 본문.
    """

    parts = [
        f"요청 유형: {request.mode}",
        f"사용자 요청: {request.message}",
    ]
    if request.session_id:
        parts.append(f"강의 세션 ID: {request.session_id}")
    if request.document_id:
        parts.append(f"문서 ID: {request.document_id}")
    if request.page_number is not None:
        parts.append(f"우선 참고할 페이지 번호: {request.page_number}")
    if request.checkpoints:
        parts.append("사용자가 모르는 항목:\n" + "\n".join(f"- {item}" for item in request.checkpoints))
    if context:
        parts.append("참고 컨텍스트:\n" + "\n\n".join(context))
    return "\n\n".join(parts)


def is_short_social_message(message: str) -> bool:
    """인사/감사/확인처럼 슬라이드 해설로 확장하면 안 되는 짧은 발화를 판별한다."""

    normalized = message.strip().lower().replace("!", "").replace(".", "").replace("?", "")
    return normalized in SHORT_REPLY_MESSAGES or len(normalized) <= 2


def strip_json_code_fence(content: str) -> str:
    """LLM 응답에서 JSON 코드펜스가 섞인 경우 순수 JSON 문자열만 추출한다."""

    stripped = content.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def parse_exam_questions(content: str) -> list[ExamQuestion]:
    """LLM이 생성한 JSON을 객관식 시험 문항 목록으로 검증한다."""

    try:
        data = json.loads(strip_json_code_fence(content))
    except json.JSONDecodeError as exc:
        raise ExamGenerationError("시험 문제 JSON을 해석하지 못했습니다.") from exc

    if isinstance(data, dict) and "questions" in data:
        data = data["questions"]
    if not isinstance(data, list):
        raise ExamGenerationError("시험 문제 응답은 배열이어야 합니다.")

    questions: list[ExamQuestion] = []
    for item in data:
        try:
            question = ExamQuestion.model_validate(item)
        except ValidationError as exc:
            raise ExamGenerationError("시험 문제 형식이 올바르지 않습니다.") from exc

        if len(question.options) != EXAM_OPTION_COUNT:
            raise ExamGenerationError("각 시험 문제는 보기 4개를 가져야 합니다.")
        if not 0 <= question.correct_option_index < len(question.options):
            raise ExamGenerationError("시험 문제의 정답 번호가 올바르지 않습니다.")
        if not question.question.strip() or any(not option.strip() for option in question.options):
            raise ExamGenerationError("시험 문제와 보기는 비어 있을 수 없습니다.")
        questions.append(question)

    if len(questions) != EXAM_QUESTION_COUNT:
        raise ExamGenerationError(f"시험 문제는 정확히 {EXAM_QUESTION_COUNT}개여야 합니다.")
    return questions


def build_exam_prompt(*, lecture_context: str, checkpoints: list[str], chat_messages: list[str]) -> str:
    """강의 자료와 학습 기록을 LLM 시험 생성 프롬프트로 구성한다."""

    parts = [
        "아래 강의 자료를 기반으로 신입사원 학습 확인용 객관식 시험을 생성하세요.",
        f"문항 수: {EXAM_QUESTION_COUNT}개",
        f"각 문항 보기 수: {EXAM_OPTION_COUNT}개",
        "정답 인덱스는 0부터 시작합니다.",
        "강의 자료에 근거한 문제만 내고, 자료에 없는 사실은 만들지 마세요.",
        "사용자가 어려워한 체크포인트와 질문 기록을 우선 반영하세요.",
        '응답은 {"questions": [...]} 형태의 JSON만 반환하세요. 마크다운은 포함하지 마세요.',
        "각 question 객체 필드: question, options, correct_option_index, explanation, source_hint",
        "",
        "강의 자료:",
        lecture_context[:MAX_EXAM_CONTEXT_CHARS],
    ]
    if checkpoints:
        parts.extend(["", "사용자 체크포인트:", "\n".join(f"- {item}" for item in checkpoints[:20])])
    if chat_messages:
        parts.extend(["", "사용자 질문 기록:", "\n".join(f"- {item}" for item in chat_messages[:20])])
    return "\n".join(parts)


async def get_page_context(request: ChatRequest) -> list[str]:
    """채팅 요청의 문서/페이지 정보로 페이지 텍스트 컨텍스트를 조회한다."""

    if request.mode != "explain_page" and is_short_social_message(request.message):
        return []
    if not request.document_id or request.page_number is None:
        return []
    page = await document_page_crud.get_by_document_and_page(request.document_id, request.page_number)
    if page is None or not page.text.strip():
        recovered_text = await recover_page_text(request.document_id, request.page_number)
        if not recovered_text:
            return []
        return [f"현재 슬라이드 {request.page_number} 텍스트:\n{recovered_text}"]
    return [f"현재 슬라이드 {page.page_number} 텍스트:\n{page.text}"]


async def recover_page_text(document_id: str, page_number: int) -> str:
    """저장된 페이지 텍스트가 비어 있을 때 원본 문서에서 해당 페이지만 재추출한다."""

    document = await document_crud.get_by_id(document_id)
    page = await document_page_crud.get_by_document_and_page(document_id, page_number)
    if document is None or page is None:
        return ""

    pages = await document_service.extract_pages(Path(document.file_path), document.file_type)
    text_by_page = {item["page_number"]: str(item.get("text") or "") for item in pages}
    text = text_by_page.get(page_number, "").strip()
    if text:
        await document_page_crud.update_text(page, text)
    return text


async def build_lecture_exam_context(document_ids: list[str]) -> str:
    """강의 세션 문서들의 페이지 텍스트를 시험 생성 컨텍스트로 합친다."""

    context_parts: list[str] = []
    remaining_chars = MAX_EXAM_CONTEXT_CHARS
    for document_id in document_ids:
        pages = await document_page_crud.list_by_document(document_id)
        for page in pages:
            text = page.text.strip()
            if not text:
                continue
            section = f"문서 {document_id} / {page.page_number}페이지:\n{text}"
            if len(section) > remaining_chars:
                context_parts.append(section[:remaining_chars])
                return "\n\n".join(context_parts)
            context_parts.append(section)
            remaining_chars -= len(section)
            if remaining_chars <= 0:
                return "\n\n".join(context_parts)
    return "\n\n".join(context_parts)


def build_messages(request: ChatRequest, context: list[str]) -> list[dict[str, str]]:
    """OpenAI Chat Completions 메시지 배열을 구성한다.

    Args:
        request: 채팅 요청.
        context: RAG 컨텍스트 목록.

    Returns:
        list[dict[str, str]]: system/user 메시지 배열.
    """

    # 질문 모드에서는 과한 슬라이드 설명 대신 짧은 답변 정책을 명시한다
    user_prompt = build_user_prompt(request, context)
    if request.mode == "question":
        user_prompt += "\n\n답변 지침: 사용자가 페이지 설명을 직접 요청하지 않았다면 현재 페이지 전체를 요약하지 말고 질문에만 답하세요."
    if request.mode == "explain_page":
        user_prompt += """

페이지 해설 지침:
마크다운 헤더(#)와 리스트(-, *)를 적절히 활용해 읽기 쉽게 구성하세요.
"안녕하세요! 이번 페이지에서는..." 처럼 친근하게 시작해서 핵심 내용을 설명하고, 마지막에 "이 부분은 꼭 기억해두세요!"처럼 따뜻하게 마무리하세요.
""".strip()
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


async def stream_chat(request: ChatRequest) -> AsyncIterator[ChatStreamEvent]:
    """OpenAI 스트리밍 응답을 SSE 이벤트로 변환해 yield한다.

    Args:
        request: 채팅 요청. message/document_id/page_number/checkpoints 포함.

    Yields:
        ChatStreamEvent: delta(토큰 조각) 이벤트와 done/error 이벤트.
    """

    # 페이지 번호가 있으면 현재 슬라이드 텍스트를 우선 컨텍스트로 주입한다
    context = await get_page_context(request)

    # 요청과 임시 컨텍스트를 OpenAI 메시지 포맷으로 변환한다
    messages = build_messages(request, context)

    try:
        # 설정값으로 OpenAI 비동기 클라이언트를 생성한다
        client = get_openai_client()

        # OpenAI Chat Completions를 스트리밍 모드로 호출한다
        stream = await client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield ChatStreamEvent(type="delta", text=delta)
        yield ChatStreamEvent(type="done")
    except asyncio.CancelledError:
        yield ChatStreamEvent(type="error", error="클라이언트 연결이 종료되어 응답 생성을 중단했습니다.")
    except APIError as exc:
        yield ChatStreamEvent(type="error", error=f"OpenAI 호출 중 오류가 발생했습니다: {exc}")


async def generate_chat_answer(request: ChatRequest) -> str:
    """사용자 질문에 대한 답변을 스트리밍 없이 한 번에 생성한다."""

    context = await get_page_context(request)
    messages = build_messages(request, context)
    client = get_openai_client()
    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=messages,
        stream=False,
    )
    content = response.choices[0].message.content if response.choices else None
    return (content or "").strip()


async def generate_page_explanation(request: ChatRequest) -> str:
    """현재 페이지 설명을 스트리밍 없이 하나의 텍스트로 생성한다."""

    context = await get_page_context(request)
    messages = build_messages(request, context)
    client = get_openai_client()
    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=messages,
        stream=False,
        max_tokens=1500,
    )
    content = response.choices[0].message.content if response.choices else None
    return (content or "").strip()


async def generate_exam_questions(
    *,
    document_ids: list[str],
    checkpoints: list[str],
    chat_messages: list[str],
) -> list[ExamQuestion]:
    """강의 자료와 사용자의 학습 기록을 기반으로 객관식 시험 문제를 생성한다."""

    lecture_context = await build_lecture_exam_context(document_ids)
    if not lecture_context.strip():
        raise ExamGenerationError("시험을 생성할 강의 문서 텍스트가 없습니다.")

    messages = [
        {
            "role": "system",
            "content": "당신은 강의 내용 이해도를 평가하는 객관식 시험 출제자입니다. 반드시 유효한 JSON만 응답하세요.",
        },
        {
            "role": "user",
            "content": build_exam_prompt(
                lecture_context=lecture_context,
                checkpoints=checkpoints,
                chat_messages=chat_messages,
            ),
        },
    ]
    client = get_openai_client()
    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=messages,
        stream=False,
        max_tokens=2200,
    )
    content = response.choices[0].message.content if response.choices else None
    if not content:
        raise ExamGenerationError("시험 문제 생성 응답이 비어 있습니다.")
    return parse_exam_questions(content)
