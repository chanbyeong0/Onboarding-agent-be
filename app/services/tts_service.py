"""tts_service 모듈은 ClovaTTS 호출과 생성된 오디오 파일 저장을 담당한다."""

from pathlib import Path

import anyio
import httpx

from app.core.config import settings


class TTSConfigurationError(RuntimeError):
    """TTS 호출에 필요한 설정이 없을 때 발생한다."""


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

    if not settings.ncp_tts_client_id or not settings.ncp_tts_client_secret:
        raise TTSConfigurationError("ClovaTTS API 키가 설정되지 않았습니다.")

    output_path = build_tts_path(
        session_id=session_id,
        document_id=document_id,
        user_id=user_id,
        page_number=page_number,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    headers = {
        "X-NCP-APIGW-API-KEY-ID": settings.ncp_tts_client_id,
        "X-NCP-APIGW-API-KEY": settings.ncp_tts_client_secret,
    }
    data = {
        "speaker": settings.ncp_tts_speaker,
        "volume": settings.ncp_tts_volume,
        "speed": settings.ncp_tts_speed,
        "pitch": settings.ncp_tts_pitch,
        "text": text[:5000],
        "format": settings.ncp_tts_format,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(settings.ncp_tts_api_url, headers=headers, data=data)
        response.raise_for_status()

    await anyio.Path(output_path).write_bytes(response.content)
    return str(output_path)
