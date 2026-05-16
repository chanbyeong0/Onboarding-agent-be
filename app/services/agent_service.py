"""
agent_service 모듈은 OpenAI Chat Completions 스트리밍을 사용해
사용자 질문에 대한 토큰 단위 응답을 생성하고 SSE로 전달할 수 있도록 한다.
RAG 컨텍스트 주입 지점은 TODO로 표시되어 있다.
"""

import asyncio
from collections.abc import AsyncIterator

from openai import APIError, AsyncOpenAI

from app.crud import document_page as document_page_crud
from app.core.config import settings
from app.schemas.chat import ChatRequest, ChatStreamEvent

SYSTEM_PROMPT = """
당신은 사내 신입사원 온보딩을 돕는 AI 사수입니다.
답변은 친절하고 구체적으로 작성하되, 신입사원이 바로 행동할 수 있게 단계와 예시를 포함하세요.
문서 컨텍스트가 부족하면 모르는 내용을 지어내지 말고 추가 자료 확인이 필요하다고 말하세요.
강의 슬라이드 설명 요청이면 현재 페이지의 핵심 개념, 실무에서 중요한 이유, 신입이 확인할 포인트를 간결하게 설명하세요.
""".strip()


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


async def get_page_context(request: ChatRequest) -> list[str]:
    """채팅 요청의 문서/페이지 정보로 페이지 텍스트 컨텍스트를 조회한다."""

    if not request.document_id or request.page_number is None:
        return []
    page = await document_page_crud.get_by_document_and_page(request.document_id, request.page_number)
    if page is None or not page.text.strip():
        return []
    return [f"현재 슬라이드 {page.page_number} 텍스트:\n{page.text}"]


def build_messages(request: ChatRequest, context: list[str]) -> list[dict[str, str]]:
    """OpenAI Chat Completions 메시지 배열을 구성한다.

    Args:
        request: 채팅 요청.
        context: RAG 컨텍스트 목록.

    Returns:
        list[dict[str, str]]: system/user 메시지 배열.
    """

    # 요청과 RAG 컨텍스트를 하나의 사용자 프롬프트로 합성한다
    user_prompt = build_user_prompt(request, context)
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
