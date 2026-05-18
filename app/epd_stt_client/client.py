"""EPD/STT 비동기 클라이언트."""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
from typing import Awaitable, Callable, Optional

import websockets

from ._filters import is_noise
from .exceptions import EpdNotConnected, EpdReadyTimeout
from .models import EpdResponse
from .protocol import build_audio_frame, build_config_message

log = logging.getLogger(__name__)

OnSttResult = Callable[[EpdResponse], Awaitable[None]]
OnStatus = Callable[[EpdResponse], Awaitable[None]]


class EpdSttClient:
    """단일 EPD WebSocket 세션을 관리하는 클라이언트."""

    def __init__(
        self,
        url: str = "wss://api.magovoice.com/epdx/",
        language: str = "ko",
        ready_timeout: float = 5.0,
        min_confidence: float = 0.3,
        filter_noise: bool = True,
        on_stt_result: Optional[OnSttResult] = None,
        on_status: Optional[OnStatus] = None,
        extra_headers: Optional[dict[str, str]] = None,
    ):
        self.url = url
        self.language = language
        self.ready_timeout = ready_timeout
        self.min_confidence = min_confidence
        self.filter_noise = filter_noise
        self.on_stt_result = on_stt_result
        self.on_status = on_status
        self.extra_headers = extra_headers

        self._ws = None
        self._epd_session_id: Optional[str] = None
        self._ready = asyncio.Event()
        self._recv_task: Optional[asyncio.Task] = None

    @property
    def epd_session_id(self) -> Optional[str]:
        """EPD READY 응답에서 받은 session_id."""

        return self._epd_session_id

    @property
    def is_ready(self) -> bool:
        """오디오 송신 가능한 상태인지 확인한다."""

        return self._ready.is_set() and self._ws is not None

    async def connect(self) -> None:
        """EPD 서버에 연결하고 READY 핸드셰이크를 완료한다."""

        if self._ws is not None:
            return

        connect_kwargs = {"max_size": None}
        if self.extra_headers:
            signature = inspect.signature(websockets.connect)
            header_arg = "additional_headers" if "additional_headers" in signature.parameters else "extra_headers"
            connect_kwargs[header_arg] = self.extra_headers

        self._ws = await websockets.connect(self.url, **connect_kwargs)
        self._recv_task = asyncio.create_task(self._recv_loop(), name="epd-recv")

        await self._ws.send(build_config_message(language=self.language))
        try:
            await asyncio.wait_for(self._ready.wait(), timeout=self.ready_timeout)
        except asyncio.TimeoutError as e:
            await self.close()
            raise EpdReadyTimeout(f"READY 응답을 {self.ready_timeout}s 안에 받지 못함") from e

        log.info("EPD 연결 준비 완료: session_id=%s", self._epd_session_id)

    async def send_audio(self, pcm: bytes) -> None:
        """PCM 청크를 EPD 바이너리 프레임으로 감싸 전송한다."""

        if not self.is_ready or self._ws is None or self._epd_session_id is None:
            raise EpdNotConnected("send_audio: 아직 READY 상태가 아닙니다")
        await self._ws.send(build_audio_frame(self._epd_session_id, pcm))

    async def close(self) -> None:
        """수신 태스크와 WebSocket 연결을 정리한다."""

        if self._recv_task and not self._recv_task.done():
            self._recv_task.cancel()
            try:
                await self._recv_task
            except asyncio.CancelledError:
                pass
            except Exception:
                log.exception("EPD 수신 태스크 정리 중 예외")
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:
                log.exception("EPD WebSocket 종료 중 예외")
        self._ws = None
        self._epd_session_id = None
        self._ready.clear()

    async def __aenter__(self) -> "EpdSttClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def _recv_loop(self) -> None:
        assert self._ws is not None
        try:
            async for raw in self._ws:
                payload = raw.decode("utf-8", errors="ignore").strip() if isinstance(raw, (bytes, bytearray)) else raw.strip()
                if payload:
                    await self._handle_message(payload)
        except websockets.ConnectionClosed as e:
            log.info("EPD 연결 종료: code=%s reason=%s", e.code, e.reason)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("EPD 수신 루프 예외")

    async def _handle_message(self, payload: str) -> None:
        if not (payload.startswith("{") and payload.endswith("}")):
            log.debug("EPD: JSON 아님, 무시 - %r", payload[:80])
            return

        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            log.warning("EPD: JSON 파싱 실패 - %r", payload[:120])
            return

        if data.get("status") == "READY":
            sid = data.get("session_id")
            if sid:
                self._epd_session_id = sid
                self._ready.set()
                log.info("EPD READY 수신: session_id=%s", sid)
            return

        resp = EpdResponse.from_dict(data)
        if self.on_status:
            try:
                await self.on_status(resp)
            except Exception:
                log.exception("on_status 콜백 예외")

        if resp.is_end_with_stt:
            decoded = resp.decoded_text()
            if self.filter_noise and is_noise(decoded, resp.confidence, self.min_confidence):
                log.debug("EPD: 노이즈 무시 - text=%r conf=%.2f", decoded, resp.confidence)
                return
            resp.text = decoded
            log.info("EPD STT candidate: text=%r conf=%.2f", resp.text, resp.confidence)
            if self.on_stt_result:
                try:
                    await self.on_stt_result(resp)
                except Exception:
                    log.exception("on_stt_result 콜백 예외")
