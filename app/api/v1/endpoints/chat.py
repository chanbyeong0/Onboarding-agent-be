"""chat 엔드포인트는 사용자 질문에 대한 일반 JSON 답변을 반환한다."""

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.crud import chat_message as chat_message_crud
from app.crud import document as document_crud
from app.crud import lecture_session as lecture_session_crud
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse
from app.services import agent_service, tts_service

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatTtsRequest(BaseModel):
    text: str


@router.post("")
async def chat(
    chat_request: ChatRequest,
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    """사용자 질문에 대한 AI 응답을 일반 JSON으로 반환한다.

    Args:
        chat_request: 채팅 요청 데이터.
        current_user: JWT 토큰에서 조회한 현재 사용자.

    Returns:
        ChatResponse: 생성된 답변 텍스트.
    """

    if chat_request.session_id:
        session = await lecture_session_crud.get_by_id(chat_request.session_id)
        if session is None:
            from fastapi import HTTPException, status

            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="강의 세션을 찾을 수 없습니다.")
    if chat_request.document_id:
        document = await document_crud.get_by_id(chat_request.document_id)
        if document is None:
            from fastapi import HTTPException, status

            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문서를 찾을 수 없습니다.")

    # 연동 안정성을 위해 OpenAI 응답을 모두 받은 뒤 단일 JSON으로 반환한다
    answer = await agent_service.generate_chat_answer(chat_request)
    if chat_request.session_id:
        await chat_message_crud.create(
            session_id=chat_request.session_id,
            user_id=str(current_user.id),
            message=chat_request.message,
            answer=answer,
            document_id=chat_request.document_id,
            page_number=chat_request.page_number,
        )
    return ChatResponse(answer=answer)


@router.post("/tts")
async def synthesize_chat_tts(
    tts_request: ChatTtsRequest,
    current_user: User = Depends(get_current_user),
) -> Response:
    """채팅 응답 텍스트를 TTS로 변환해 mp3 바이트를 직접 반환한다."""

    _ = current_user
    import tempfile
    from pathlib import Path

    import anyio
    import httpx

    from app.core.config import settings

    if not settings.ncp_tts_client_id or not settings.ncp_tts_client_secret:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="TTS 서비스가 설정되지 않았습니다.")

    clean_text = tts_service.strip_markdown(tts_request.text)[:5000]
    headers = {
        "X-NCP-APIGW-API-KEY-ID": settings.ncp_tts_client_id,
        "X-NCP-APIGW-API-KEY": settings.ncp_tts_client_secret,
    }
    data = {
        "speaker": settings.ncp_tts_speaker,
        "volume": settings.ncp_tts_volume,
        "speed": settings.ncp_tts_speed,
        "pitch": settings.ncp_tts_pitch,
        "text": clean_text,
        "format": settings.ncp_tts_format,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(settings.ncp_tts_api_url, headers=headers, data=data)
        response.raise_for_status()

    return Response(content=response.content, media_type="audio/mpeg")
