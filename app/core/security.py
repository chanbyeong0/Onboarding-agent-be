"""
security 모듈은 JWT 액세스 토큰과 비밀번호 해싱을 처리한다.
API 인증 계층에서 사용자 식별과 자격 증명 검증에 사용한다.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """평문 비밀번호를 bcrypt 해시로 변환한다.

    Args:
        password: 사용자가 입력한 평문 비밀번호.

    Returns:
        str: 데이터베이스에 저장할 bcrypt 해시 문자열.
    """

    # passlib 컨텍스트가 bcrypt salt와 라운드를 안전하게 관리한다
    return password_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """평문 비밀번호가 저장된 bcrypt 해시와 일치하는지 검증한다.

    Args:
        plain_password: 로그인 요청에 포함된 평문 비밀번호.
        hashed_password: MongoDB에 저장된 bcrypt 해시.

    Returns:
        bool: 비밀번호가 일치하면 True, 그렇지 않으면 False.
    """

    # passlib 검증 함수로 해시 알고리즘 세부사항을 숨긴다
    return password_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """사용자 식별자를 담은 JWT 액세스 토큰을 생성한다.

    Args:
        subject: 토큰 subject에 넣을 사용자 ID 문자열.
        expires_delta: 기본 만료 시간 대신 사용할 만료 간격.

    Returns:
        str: Authorization Bearer 헤더에 사용할 JWT 문자열.
    """

    expire_delta = expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    expire_at = datetime.now(UTC) + expire_delta
    payload: dict[str, Any] = {"sub": subject, "exp": expire_at, "type": "access"}

    # 설정된 시크릿과 알고리즘으로 API 클라이언트에 전달할 토큰을 만든다
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str, token_id: str, expires_delta: timedelta | None = None) -> str:
    """사용자 식별자와 토큰 ID를 담은 JWT 리프레시 토큰을 생성한다.

    Args:
        subject: 토큰 subject에 넣을 사용자 ID 문자열.
        token_id: 서버 저장소에서 refresh 세션을 찾기 위한 고유 ID.
        expires_delta: 기본 만료 시간 대신 사용할 만료 간격.

    Returns:
        str: access token 재발급에 사용할 refresh JWT 문자열.
    """

    expire_delta = expires_delta or timedelta(days=settings.refresh_token_expire_days)
    expire_at = datetime.now(UTC) + expire_delta
    payload: dict[str, Any] = {"sub": subject, "jti": token_id, "exp": expire_at, "type": "refresh"}

    # access token과 같은 시크릿/알고리즘을 사용하되 type으로 용도를 구분한다
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any] | None:
    """JWT 토큰을 검증하고 페이로드를 반환한다.

    Args:
        token: Authorization Bearer 헤더에서 추출한 JWT 문자열.

    Returns:
        dict[str, Any] | None: 검증된 페이로드. 실패하면 None.
    """

    try:
        # python-jose가 서명, 알고리즘, 만료 시간을 함께 검증한다
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None


def decode_refresh_token(token: str) -> dict[str, Any] | None:
    """리프레시 토큰을 검증하고 refresh 타입 페이로드만 반환한다.

    Args:
        token: 클라이언트가 localStorage에서 전달한 refresh JWT 문자열.

    Returns:
        dict[str, Any] | None: 검증된 refresh payload. 실패하면 None.
    """

    # 공통 JWT 검증 함수로 서명과 만료 시간을 먼저 확인한다
    payload = decode_token(token)
    if payload is None or payload.get("type") != "refresh":
        return None
    return payload
