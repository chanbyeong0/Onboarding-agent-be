"""STT 결과 노이즈 필터링."""

from typing import Optional

ALLOWED_SINGLE_CHARS = {"응", "왜", "뭐"}


def is_noise(text: Optional[str], confidence: float, min_confidence: float = 0.3) -> bool:
    """빈 텍스트, 낮은 신뢰도, 대부분의 1글자 응답을 노이즈로 본다."""

    if not text or not text.strip():
        return True
    if confidence < min_confidence:
        return True
    stripped = text.strip()
    if len(stripped) == 1 and stripped not in ALLOWED_SINGLE_CHARS:
        return True
    return False
