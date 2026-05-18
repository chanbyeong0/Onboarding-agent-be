"""
users 엔드포인트는 회원가입, 로그인, 내 정보 조회 API를 제공한다.
로그인 성공 시 access/refresh JWT를 JSON으로 반환한다.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.user import LogoutRequest, RefreshRequest, Token, UserCreate, UserLogin, UserResponse
from app.services import auth_service

router = APIRouter(prefix="/users", tags=["users"])


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

    try:
        return await auth_service.register_user(user_in)
    except auth_service.UserRegistrationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


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

    try:
        return await auth_service.login_user(login_in)
    except auth_service.AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


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

    try:
        return await auth_service.refresh_access_token(refresh_in.refresh_token)
    except auth_service.AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.post("/logout")
async def logout(logout_in: LogoutRequest) -> dict[str, str]:
    """리프레시 세션을 폐기해 로그아웃 처리한다.

    Args:
        logout_in: 폐기할 refresh token을 담은 요청.

    Returns:
        dict[str, str]: 로그아웃 처리 결과.
    """

    return await auth_service.logout_user(logout_in.refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """현재 인증된 사용자 정보를 반환한다.

    Args:
        current_user: JWT 토큰에서 조회한 현재 사용자.

    Returns:
        UserResponse: 현재 사용자 정보.
    """

    return auth_service.to_user_response(current_user)
