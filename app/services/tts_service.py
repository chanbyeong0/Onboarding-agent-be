"""tts_service 모듈은 ClovaTTS 호출과 생성된 오디오 파일 저장을 담당한다."""

import re
from pathlib import Path

import anyio
import httpx

from app.core.config import settings


class TTSConfigurationError(RuntimeError):
    """TTS 호출에 필요한 설정이 없을 때 발생한다."""


def build_tts_headers() -> dict[str, str]:
    """ClovaTTS 호출에 필요한 인증 헤더를 생성한다."""

    if not settings.ncp_tts_client_id or not settings.ncp_tts_client_secret:
        raise TTSConfigurationError("ClovaTTS API 키가 설정되지 않았습니다.")
    return {
        "X-NCP-APIGW-API-KEY-ID": settings.ncp_tts_client_id,
        "X-NCP-APIGW-API-KEY": settings.ncp_tts_client_secret,
    }


def build_tts_payload(text: str) -> dict[str, str]:
    """ClovaTTS 요청 body를 생성한다."""

    return {
        "speaker": settings.ncp_tts_speaker,
        "volume": settings.ncp_tts_volume,
        "speed": settings.ncp_tts_speed,
        "pitch": settings.ncp_tts_pitch,
        "text": strip_markdown(text)[:5000],
        "format": settings.ncp_tts_format,
    }


async def synthesize_to_bytes(text: str) -> bytes:
    """ClovaTTS로 텍스트를 mp3 바이트로 변환한다."""

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            settings.ncp_tts_api_url,
            headers=build_tts_headers(),
            data=build_tts_payload(text),
        )
        response.raise_for_status()
    return response.content


def strip_markdown(text: str) -> str:
    """TTS 전달 전 마크다운 문법 기호를 제거해 자연스러운 음성을 생성한다."""

    # 헤더 (#, ##, ###)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # 굵게/기울임 (**, __, *, _)
    text = re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", text)
    text = re.sub(r"_{1,3}(.+?)_{1,3}", r"\1", text)
    # 인라인 코드 (`code`)
    text = re.sub(r"`(.+?)`", r"\1", text)
    # 코드 블록 (```...```)
    text = re.sub(r"```[\s\S]*?```", "", text)
    # 링크 [text](url) → text
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
    # 이미지 ![alt](url) 제거
    text = re.sub(r"!\[.*?\]\(.+?\)", "", text)
    # 수평선 (---, ***)
    text = re.sub(r"^[-*]{3,}\s*$", "", text, flags=re.MULTILINE)
    # 인용 (>)
    text = re.sub(r"^>\s+", "", text, flags=re.MULTILINE)
    # 리스트 기호 (-, *, +)
    text = re.sub(r"^[-*+]\s+", "", text, flags=re.MULTILINE)
    # 순서 있는 리스트 (1. 2.)
    text = re.sub(r"^\d+\.\s+", "", text, flags=re.MULTILINE)
    # 연속 공백/줄바꿈 정리
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def build_tts_path(*, session_id: str, document_id: str, user_id: str, page_number: int) -> Path:
    """페이지 해설 TTS 파일 저장 경로를 생성한다."""

    return Path(settings.upload_dir) / "tts" / session_id / document_id / user_id / f"page-{page_number}.mp3"


async def synthesize_to_file(
    *,
    text: str,
    session_id: str,
    document_id: str,
    user_id: str,
    page_number: int,
) -> str:
    """ClovaTTS로 텍스트를 mp3 파일로 변환하고 저장 경로를 반환한다."""

    output_path = build_tts_path(
        session_id=session_id,
        document_id=document_id,
        user_id=user_id,
        page_number=page_number,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    await anyio.Path(output_path).write_bytes(await synthesize_to_bytes(text))
    return str(output_path)
