"""
config 모듈은 환경변수를 Pydantic Settings로 로드한다.
MongoDB, OpenAI, JWT, 업로드 디렉터리 설정을 한곳에서 관리한다.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """애플리케이션 실행에 필요한 환경 설정을 정의한다.

    Args:
        BaseSettings: 환경변수와 .env 파일을 읽어 필드를 채우는 Pydantic 설정 기반 클래스.
    """

    mongodb_url: str = Field(default="mongodb://root:example@localhost:27017", alias="MONGODB_URL")
    mongodb_db_name: str = Field(default="onboarding", alias="MONGODB_DB_NAME")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    openai_base_url: str | None = Field(default=None, alias="OPENAI_BASE_URL")
    ncp_tts_api_url: str = Field(
        default="https://naveropenapi.apigw.ntruss.com/tts-premium/v1/tts",
        alias="NCP_TTS_API_URL",
    )
    ncp_tts_client_id: str = Field(default="", alias="NCP_TTS_CLIENT_ID")
    ncp_tts_client_secret: str = Field(default="", alias="NCP_TTS_CLIENT_SECRET")
    ncp_tts_speaker: str = Field(default="vhyeri", alias="NCP_TTS_SPEAKER")
    ncp_tts_volume: str = Field(default="0", alias="NCP_TTS_VOLUME")
    ncp_tts_speed: str = Field(default="0", alias="NCP_TTS_SPEED")
    ncp_tts_pitch: str = Field(default="0", alias="NCP_TTS_PITCH")
    ncp_tts_format: str = Field(default="mp3", alias="NCP_TTS_FORMAT")
    jwt_secret_key: str = Field(default="change-me", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=60, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=14, alias="REFRESH_TOKEN_EXPIRE_DAYS")
    upload_dir: str = Field(default="./uploads", alias="UPLOAD_DIR")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache
def get_settings() -> Settings:
    """환경 설정 객체를 캐시해 반복 생성 비용을 줄인다.

    Returns:
        Settings: 환경변수와 .env 파일이 반영된 설정 객체.
    """

    return Settings()


settings = get_settings()
