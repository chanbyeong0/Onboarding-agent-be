"""EPD 응답 모델 및 상태 enum."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional


class EpdStatus(IntEnum):
    """EPD 서버가 내려주는 음성 처리 상태 코드."""

    WAITING = 0
    SPEECH = 1
    PAUSE = 2
    END = 3
    TIMEOUT = 4
    MAX_TIMEOUT = 5
    NONE = 9


_UNICODE_ESC = re.compile(r"\\u([0-9a-fA-F]{4})")


def decode_unicode_escapes(s: Optional[str]) -> Optional[str]:
    """문자열에 그대로 들어온 유니코드 이스케이프를 실제 문자로 변환한다."""

    if not s or "\\u" not in s:
        return s
    return _UNICODE_ESC.sub(lambda m: chr(int(m.group(1), 16)), s)


@dataclass
class EpdResponse:
    """EPD/STT 서버의 일반 상태 응답."""

    status: int
    session_id: Optional[str] = None
    speech_score: float = 0.0
    text: Optional[str] = None
    confidence: float = 0.0
    speech_path: Optional[str] = None
    speech_duration: float = 0.0
    data_type: Optional[str] = None

    @classmethod
    def from_dict(cls, d: dict) -> "EpdResponse":
        """JSON dict를 안정적으로 `EpdResponse`로 변환한다."""

        raw_status = d.get("status", -1)
        return cls(
            status=int(raw_status) if not isinstance(raw_status, str) else -1,
            session_id=d.get("session_id"),
            speech_score=float(d.get("speech_score") or 0.0),
            text=d.get("text"),
            confidence=float(d.get("confidence") or 0.0),
            speech_path=d.get("speech_path"),
            speech_duration=float(d.get("speech_duration") or 0.0),
            data_type=d.get("data_type"),
        )

    @property
    def is_end_with_stt(self) -> bool:
        """발화 종료와 함께 STT 텍스트가 포함된 응답인지 확인한다."""

        return self.status == EpdStatus.END and bool(self.text and self.text.strip())

    def decoded_text(self) -> Optional[str]:
        """STT 텍스트의 유니코드 이스케이프를 해제한다."""

        return decode_unicode_escapes(self.text)
