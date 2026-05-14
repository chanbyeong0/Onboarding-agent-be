"""
router 모듈은 v1 API 엔드포인트를 하나의 APIRouter로 통합한다.
main.py는 이 라우터를 /api/v1 prefix 아래에 등록한다.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import chat, checkpoint, document, users

api_router = APIRouter()

# 사용자 인증과 내 정보 API를 v1 라우터에 등록한다
api_router.include_router(users.router)

# 문서 업로드와 조회 API를 v1 라우터에 등록한다
api_router.include_router(document.router)

# 사용자 체크포인트 API를 v1 라우터에 등록한다
api_router.include_router(checkpoint.router)

# SSE 채팅 API를 v1 라우터에 등록한다
api_router.include_router(chat.router)
