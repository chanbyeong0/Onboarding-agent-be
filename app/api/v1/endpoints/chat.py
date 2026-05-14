"""
chat 엔드포인트는 OpenAI 스트림을 SSE 형식으로 클라이언트에 중계한다.
STT와 TTS는 프론트엔드가 담당하고, 백엔드는 텍스트 토큰만 전송한다.
"""

from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.chat import ChatRequest
from app.services import agent_service

router = APIRouter(prefix="/chat", tags=["chat"])


async def build_sse_events(request: Request, chat_request: ChatRequest) -> AsyncIterator[dict[str, str]]:
    """채팅 스트림 이벤트를 SSE 응답 형식으로 변환한다.

    Args:
        request: 클라이언트 연결 상태를 확인할 FastAPI 요청 객체.
        chat_request: 사용자 채팅 요청.

    Yields:
        dict[str, str]: sse-starlette가 직렬화할 SSE 이벤트 데이터.
    """

    # 에이전트 서비스가 생성하는 OpenAI 토큰 스트림을 순차적으로 읽는다
    async for event in agent_service.stream_chat(chat_request):
        # 클라이언트가 연결을 끊었으면 OpenAI 스트림 중계를 중단한다
        if await request.is_disconnected():
            break
        yield {"data": event.model_dump_json(exclude_none=True)}


@router.post("")
async def chat(
    request: Request,
    chat_request: ChatRequest,
    current_user: User = Depends(get_current_user),
) -> EventSourceResponse:
    """사용자 질문에 대한 AI 응답을 SSE 스트림으로 반환한다.

    Args:
        request: 클라이언트 연결 상태를 확인할 FastAPI 요청 객체.
        chat_request: 채팅 요청 데이터.
        current_user: JWT 토큰에서 조회한 현재 사용자.

    Returns:
        EventSourceResponse: text/event-stream 형식의 스트리밍 응답.
    """

    _ = current_user

    # OpenAI 스트림 이벤트를 SSE 응답으로 감싸 클라이언트에 전달한다
    return EventSourceResponse(
        build_sse_events(request, chat_request),
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
