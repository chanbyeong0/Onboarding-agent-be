"""
users 엔드포인트는 회원가입, 로그인, 내 정보 조회 API를 제공한다.
로그인 성공 시 access/refresh JWT를 JSON으로 반환한다.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.seed import ADMIN_EMAIL
from app.core.security import create_access_token, create_refresh_token, decode_refresh_token
from app.crud import refresh_token as refresh_token_crud
from app.crud import user as user_crud
from app.models.user import User
from app.schemas.user import LogoutRequest, RefreshRequest, Token, UserCreate, UserLogin, UserResponse

router = APIRouter(prefix="/users", tags=["users"])


def to_user_response(user: User) -> UserResponse:
    """User 문서를 API 응답 스키마로 변환한다.

    Args:
        user: MongoDB에서 조회한 User 문서.

    Returns:
        UserResponse: 클라이언트에 반환할 사용자 응답.
    """

    return UserResponse(id=str(user.id), email=user.email, name=user.name, role=user.role, created_at=user.created_at)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate) -> UserResponse:
    """새 사용자를 등록한다.

    Args:
        user_in: 회원가입 요청 데이터.

    Returns:
        UserResponse: 생성된 사용자 정보.

    Raises:
        HTTPException: 이미 등록된 이메일일 때 발생한다.
    """

    # 중복 이메일 가입을 막기 위해 기존 사용자를 먼저 조회한다
    existing_user = await user_crud.get_by_email(user_in.email)
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이미 등록된 이메일입니다.")

    # 비밀번호 해싱과 사용자 저장은 CRUD 계층에 위임한다
    user = await user_crud.create(user_in)
    return to_user_response(user)


@router.post("/login", response_model=Token)
async def login(login_in: UserLogin) -> Token:
    """사용자를 인증하고 JWT 토큰을 발급한다.

    Args:
        login_in: 이메일과 비밀번호를 담은 로그인 요청.

    Returns:
        Token: Bearer 액세스 토큰.

    Raises:
        HTTPException: 인증에 실패했을 때 발생한다.
    """

    # 이메일과 비밀번호 검증을 사용자 CRUD 계층에 위임한다
    email = ADMIN_EMAIL if login_in.email == "admin" else login_in.email
    user = await user_crud.authenticate(email, login_in.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="이메일 또는 비밀번호가 올바르지 않습니다.")

    # 인증된 사용자 ObjectId를 subject로 담아 access JWT를 만든다
    access_token = create_access_token(str(user.id))

    refresh_token_id = uuid4().hex
    refresh_expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)

    # refresh 세션을 서버에 저장해 logout과 재사용 차단이 가능하게 한다
    await refresh_token_crud.create(str(user.id), refresh_token_id, refresh_expires_at)

    # refresh token은 localStorage 저장 전제로 JSON 응답에 포함한다
    refresh_token = create_refresh_token(str(user.id), refresh_token_id)
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_in: RefreshRequest) -> Token:
    """리프레시 토큰으로 새 액세스 토큰을 발급한다.

    Args:
        refresh_in: localStorage에 저장된 refresh token을 담은 요청.

    Returns:
        Token: 새 access token과 기존 refresh token.

    Raises:
        HTTPException: refresh token이 유효하지 않거나 폐기되었을 때 발생한다.
    """

    # refresh JWT의 서명, 만료, type을 검증한다
    payload = decode_refresh_token(refresh_in.refresh_token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="리프레시 토큰이 유효하지 않습니다.")

    user_id = payload.get("sub")
    token_id = payload.get("jti")
    if not isinstance(user_id, str) or not isinstance(token_id, str):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="리프레시 토큰 정보가 올바르지 않습니다.")

    # 서버에 저장된 refresh 세션이 활성 상태인지 확인한다
    refresh_session = await refresh_token_crud.get_active(token_id)
    if refresh_session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="리프레시 토큰이 만료되었거나 폐기되었습니다.")

    # refresh token의 subject 사용자가 실제로 존재하는지 확인한다
    user = await user_crud.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="사용자를 찾을 수 없습니다.")

    # 검증된 사용자에게 새 access token을 발급한다
    access_token = create_access_token(str(user.id))
    return Token(access_token=access_token, refresh_token=refresh_in.refresh_token)


@router.post("/logout")
async def logout(logout_in: LogoutRequest) -> dict[str, str]:
    """리프레시 세션을 폐기해 로그아웃 처리한다.

    Args:
        logout_in: 폐기할 refresh token을 담은 요청.

    Returns:
        dict[str, str]: 로그아웃 처리 결과.
    """

    if logout_in.refresh_token:
        # refresh JWT를 검증해 서버 세션 token_id를 꺼낸다
        payload = decode_refresh_token(logout_in.refresh_token)
        if payload is not None and isinstance(payload.get("jti"), str):
            # token_id에 해당하는 refresh 세션을 폐기한다
            await refresh_token_crud.revoke(payload["jti"])
    return {"message": "로그아웃되었습니다."}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """현재 인증된 사용자 정보를 반환한다.

    Args:
        current_user: JWT 토큰에서 조회한 현재 사용자.

    Returns:
        UserResponse: 현재 사용자 정보.
    """

    return to_user_response(current_user)
