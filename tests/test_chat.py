"""
test_chat 모듈은 /chat SSE 엔드포인트의 기본 스트리밍 응답을 검증한다.
OpenAI API 호출은 가짜 async generator로 대체한다.
"""

import json
from collections.abc import AsyncIterator

import pytest

from app.schemas.chat import ChatRequest, ChatStreamEvent
from app.services import agent_service


async def fake_stream_chat(request: ChatRequest) -> AsyncIterator[ChatStreamEvent]:
    """테스트용 채팅 스트림을 생성한다.

    Args:
        request: 엔드포인트에서 전달한 채팅 요청.

    Yields:
        ChatStreamEvent: 고정된 delta와 done 이벤트.
    """

    _ = request
    yield ChatStreamEvent(type="delta", text="안녕하세요. ")
    yield ChatStreamEvent(type="delta", text="온보딩을 도와드릴게요.")
    yield ChatStreamEvent(type="done")


@pytest.mark.asyncio
async def test_chat_stream_returns_sse_events(client, auth_headers, monkeypatch) -> None:
    """POST /chat이 SSE delta와 done 이벤트를 반환하는지 확인한다."""

    # OpenAI 호출을 막기 위해 에이전트 스트림 함수를 테스트용 generator로 교체한다
    monkeypatch.setattr(agent_service, "stream_chat", fake_stream_chat)

    payload = {
        "message": "휴가 신청은 어떻게 하나요?",
        "document_id": "507f1f77bcf86cd799439011",
        "page_number": 1,
        "checkpoints": ["휴가 신청 경로"],
    }

    # 인증 헤더와 JSON 요청으로 SSE 채팅 엔드포인트를 호출한다
    response = await client.post("/api/v1/chat", json=payload, headers=auth_headers)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = []
    for line in response.text.splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line.removeprefix("data: ")))

    assert "".join(event.get("text", "") for event in events) == "안녕하세요. 온보딩을 도와드릴게요."
    assert events[-1]["type"] == "done"
