"""auth_service 모듈은 로그인, 토큰 재발급, 로그아웃 흐름을 담당한다."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.core.config import settings
from app.core.seed import ADMIN_EMAIL
from app.core.security import create_access_token, create_refresh_token, decode_refresh_token
from app.crud import refresh_token as refresh_token_crud
from app.crud import user as user_crud
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserLogin, UserResponse


class AuthenticationError(RuntimeError):
    """인증 또는 토큰 검증에 실패했을 때 발생한다."""


class UserRegistrationError(RuntimeError):
    """사용자 등록 요청이 유효하지 않을 때 발생한다."""


def to_user_response(user: User) -> UserResponse:
    """User 문서를 API 응답 스키마로 변환한다."""

    return UserResponse(id=str(user.id), email=user.email, name=user.name, role=user.role, created_at=user.created_at)


async def register_user(user_in: UserCreate) -> UserResponse:
    """새 사용자를 등록한다."""

    existing_user = await user_crud.get_by_email(user_in.email)
    if existing_user is not None:
        raise UserRegistrationError("이미 등록된 이메일입니다.")
    user = await user_crud.create(user_in)
    return to_user_response(user)


async def login_user(login_in: UserLogin) -> Token:
    """사용자를 인증하고 access/refresh 토큰을 발급한다."""

    email = ADMIN_EMAIL if login_in.email == "admin" else login_in.email
    user = await user_crud.authenticate(email, login_in.password)
    if user is None:
        raise AuthenticationError("이메일 또는 비밀번호가 올바르지 않습니다.")

    access_token = create_access_token(str(user.id))
    refresh_token_id = uuid4().hex
    refresh_expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    await refresh_token_crud.create(str(user.id), refresh_token_id, refresh_expires_at)

    refresh_token = create_refresh_token(str(user.id), refresh_token_id)
    return Token(access_token=access_token, refresh_token=refresh_token)


async def refresh_access_token(refresh_token: str) -> Token:
    """리프레시 토큰으로 새 액세스 토큰을 발급한다."""

    payload = decode_refresh_token(refresh_token)
    if payload is None:
        raise AuthenticationError("리프레시 토큰이 유효하지 않습니다.")

    user_id = payload.get("sub")
    token_id = payload.get("jti")
    if not isinstance(user_id, str) or not isinstance(token_id, str):
        raise AuthenticationError("리프레시 토큰 정보가 올바르지 않습니다.")

    refresh_session = await refresh_token_crud.get_active(token_id)
    if refresh_session is None:
        raise AuthenticationError("리프레시 토큰이 만료되었거나 폐기되었습니다.")

    user = await user_crud.get_by_id(user_id)
    if user is None:
        raise AuthenticationError("사용자를 찾을 수 없습니다.")

    access_token = create_access_token(str(user.id))
    return Token(access_token=access_token, refresh_token=refresh_token)


async def logout_user(refresh_token: str | None) -> dict[str, str]:
    """리프레시 세션을 폐기해 로그아웃 처리한다."""

    if refresh_token:
        payload = decode_refresh_token(refresh_token)
        if payload is not None and isinstance(payload.get("jti"), str):
            await refresh_token_crud.revoke(payload["jti"])
    return {"message": "로그아웃되었습니다."}
