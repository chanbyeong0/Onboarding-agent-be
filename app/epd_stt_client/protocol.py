"""EPD 프로토콜 헬퍼 - 프레임 빌드 및 session_id 변환."""

from __future__ import annotations

import uuid


def session_id_to_bytes(epd_session_id: str) -> bytes:
    """EPD가 발급한 session_id를 16바이트 UUID로 변환한다."""

    cleaned = epd_session_id.replace("-", "")
    if len(cleaned) == 32 and all(c in "0123456789abcdefABCDEF" for c in cleaned):
        return bytes.fromhex(cleaned)
    return uuid.UUID(epd_session_id).bytes


def build_audio_frame(epd_session_id: str, pcm: bytes, tts_status: int = 0) -> bytes:
    """오디오 프레임을 16B session UUID + 2B tts_status(BE) + PCM으로 만든다."""

    if not (0 <= tts_status <= 0xFFFF):
        raise ValueError("tts_status must fit in 2 bytes")
    return session_id_to_bytes(epd_session_id) + tts_status.to_bytes(2, "big") + pcm


def build_config_message(
    language: str = "ko",
    min_speech: float = 0.3,
    end_silence: float = 0.7,
    timeout: float = 7.0,
) -> str:
    """첫 설정 메시지를 만든다. STT 결과 수신을 위해 mode=agent를 반드시 포함한다."""

    if language not in ("ko", "ja"):
        raise ValueError(f"Unsupported language: {language}")
    return (
        f"min_speech={min_speech},end_silence={end_silence},"
        f"timeout={timeout},mode=agent,language={language}"
    )
