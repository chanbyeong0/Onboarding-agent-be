"""
main 모듈은 FastAPI 애플리케이션의 진입점이다.
CORS, 헬스체크, v1 라우터 등록, MongoDB/Beanie lifespan 초기화를 담당한다.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.db.session import close_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """애플리케이션 시작과 종료 시점의 리소스를 관리한다.

    Args:
        app: FastAPI 애플리케이션 인스턴스.

    Yields:
        None: 애플리케이션 실행 구간.
    """

    _ = app

    # MongoDB 클라이언트와 Beanie 문서 모델을 앱 시작 시 초기화한다
    await init_db()
    try:
        yield
    finally:
        # 애플리케이션 종료 시 MongoDB 클라이언트를 닫아 소켓을 정리한다
        await close_db()


app = FastAPI(title="Onboarding AI Agent API", version="0.1.0", lifespan=lifespan)

# 개발 단계에서는 모든 Origin을 허용하고, 운영 전 프론트 도메인으로 제한한다
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# v1 API 라우터를 /api/v1 prefix 아래에 등록한다
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict[str, str]:
    """서버 상태 확인용 헬스체크 응답을 반환한다.

    Returns:
        dict[str, str]: 서비스 상태를 나타내는 간단한 JSON 응답.
    """

    return {"status": "ok"}
