"""
deps 모듈은 API 엔드포인트에서 공유하는 인증 의존성을 정의한다.
JWT Bearer 토큰을 검증하고 현재 사용자 문서를 조회한다.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.security import decode_token
from app.crud import user as user_crud
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/login")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """JWT 토큰에서 현재 사용자를 조회한다.

    Args:
        token: Authorization Bearer 헤더에서 추출한 JWT 문자열.

    Returns:
        User: 인증된 사용자 문서.

    Raises:
        HTTPException: 토큰이 없거나 사용자 조회에 실패했을 때 발생한다.
    """

    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증 정보를 확인할 수 없습니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # JWT 서명과 만료 시간을 검증하고 페이로드를 복원한다
    payload = decode_token(token)
    if payload is None:
        raise credentials_error
    if payload.get("type") != "access":
        raise credentials_error

    user_id = payload.get("sub")
    if not isinstance(user_id, str):
        raise credentials_error

    # 토큰 subject에 담긴 사용자 ObjectId로 MongoDB 사용자를 조회한다
    user = await user_crud.get_by_id(user_id)
    if user is None:
        raise credentials_error
    return user
