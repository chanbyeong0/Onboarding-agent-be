"""STT WebSocket 엔드포인트는 브라우저 PCM 스트림을 EPD/STT 서버로 프록시한다."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.core.config import settings
from app.core.security import decode_token
from app.crud import user as user_crud
from app.epd_stt_client import EpdReadyTimeout, EpdResponse, EpdSttClient

router = APIRouter(prefix="/stt", tags=["stt"])
log = logging.getLogger("uvicorn.error")

ALLOWED_LANGUAGES = {"ko", "ja"}
TERMINAL_STATUSES = {4, 5}


async def authenticate_websocket(websocket: WebSocket) -> bool:
    """query token을 검증해 WebSocket 사용 가능 여부를 판단한다."""

    token = websocket.query_params.get("token")
    if not token:
        return False

    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        return False

    user_id = payload.get("sub")
    if not isinstance(user_id, str):
        return False

    # access token의 subject가 실제 사용자 문서인지 확인한다
    return await user_crud.get_by_id(user_id) is not None


def resolve_language(websocket: WebSocket) -> str:
    """요청 language가 허용값이면 사용하고, 아니면 설정 기본값으로 되돌린다."""

    requested = websocket.query_params.get("language") or settings.epd_language
    return requested if requested in ALLOWED_LANGUAGES else settings.epd_language


@router.websocket("/ws")
async def stt_ws(websocket: WebSocket) -> None:
    """브라우저에서 받은 16kHz mono Int16 PCM을 EPD/STT 서버로 전달한다."""

    await websocket.accept()
    if not await authenticate_websocket(websocket):
        log.warning("STT WebSocket authentication failed")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    language = resolve_language(websocket)
    terminal_event = asyncio.Event()
    sent_audio_chunks = 0

    async def on_status(resp: EpdResponse) -> None:
        log.info("EPD status received: status=%s conf=%.2f duration=%.2f", resp.status, resp.confidence, resp.speech_duration)
        await websocket.send_json(
            {
                "type": "status",
                "status": resp.status,
                "confidence": resp.confidence,
                "speech_score": resp.speech_score,
                "speech_duration": resp.speech_duration,
            }
        )
        if resp.status in TERMINAL_STATUSES:
            terminal_event.set()

    async def on_stt_result(resp: EpdResponse) -> None:
        log.info("EPD STT result received: text=%r conf=%.2f", resp.text, resp.confidence)
        await websocket.send_json(
            {
                "type": "stt",
                "text": resp.text,
                "confidence": resp.confidence,
                "speech_path": resp.speech_path,
                "speech_duration": resp.speech_duration,
            }
        )
        terminal_event.set()

    client = EpdSttClient(
        url=settings.epd_url,
        language=language,
        ready_timeout=settings.epd_ready_timeout,
        min_confidence=settings.epd_min_confidence,
        filter_noise=False,
        on_status=on_status,
        on_stt_result=on_stt_result,
    )

    try:
        await client.connect()
        log.info("STT WebSocket ready: language=%s session_id=%s", language, client.epd_session_id)
        await websocket.send_json({"type": "ready", "session_id": client.epd_session_id})

        while not terminal_event.is_set():
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                log.info("STT WebSocket disconnected by frontend after %s audio chunks", sent_audio_chunks)
                break
            pcm = message.get("bytes")
            if pcm:
                sent_audio_chunks += 1
                await client.send_audio(pcm)
    except WebSocketDisconnect:
        log.info("STT WebSocket disconnected after %s audio chunks", sent_audio_chunks)
    except EpdReadyTimeout as exc:
        log.warning("EPD READY timeout: %s", exc)
        await websocket.send_json({"type": "error", "error": str(exc)})
    except Exception:
        log.exception("STT WebSocket proxy failed")
        try:
            await websocket.send_json({"type": "error", "error": "STT 처리 중 오류가 발생했습니다."})
        except Exception:
            pass
    finally:
        await client.close()
