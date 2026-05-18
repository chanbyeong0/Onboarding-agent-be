"""chat 엔드포인트는 사용자 질문에 대한 일반 JSON 답변을 반환한다."""

from fastapi import APIRouter, Depends
from fastapi import HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse
from app.services import chat_service, tts_service

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

    try:
        answer = await chat_service.generate_answer(chat_request, user_id=str(current_user.id))
    except chat_service.ChatResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ChatResponse(answer=answer)


@router.post("/tts")
async def synthesize_chat_tts(
    tts_request: ChatTtsRequest,
    current_user: User = Depends(get_current_user),
) -> Response:
    """채팅 응답 텍스트를 TTS로 변환해 mp3 바이트를 직접 반환한다."""

    _ = current_user
    try:
        audio_bytes = await tts_service.synthesize_to_bytes(tts_request.text)
    except tts_service.TTSConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="TTS 서비스가 설정되지 않았습니다.") from exc
    return Response(content=audio_bytes, media_type="audio/mpeg")
