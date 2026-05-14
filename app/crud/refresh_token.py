"""
refresh_token CRUD 모듈은 refresh JWT의 서버 측 세션 생성과 폐기를 담당한다.
클라이언트가 localStorage에 보관한 refresh 토큰은 token_id로 서버 상태와 대조한다.
"""

from datetime import UTC, datetime

from beanie import PydanticObjectId

from app.models.refresh_token import RefreshToken


async def create(user_id: str, token_id: str, expires_at: datetime) -> RefreshToken:
    """리프레시 토큰 세션을 생성한다.

    Args:
        user_id: refresh token을 발급받은 사용자 ObjectId 문자열.
        token_id: JWT payload의 jti에 넣을 고유 토큰 ID.
        expires_at: refresh token 만료 시각.

    Returns:
        RefreshToken: MongoDB에 저장된 refresh 세션 문서.
    """

    refresh_token = RefreshToken(user_id=PydanticObjectId(user_id), token_id=token_id, expires_at=expires_at)

    # Beanie insert로 refresh 세션을 refresh_tokens 컬렉션에 저장한다
    return await refresh_token.insert()


async def get_active(token_id: str) -> RefreshToken | None:
    """활성 상태의 refresh 세션을 조회한다.

    Args:
        token_id: JWT payload의 jti 값.

    Returns:
        RefreshToken | None: 미폐기·미만료 세션이 있으면 반환한다.
    """

    now = datetime.now(UTC)

    # token_id, 폐기 여부, 만료 시각을 함께 확인해 재사용 가능한 세션만 조회한다
    return await RefreshToken.find_one(
        RefreshToken.token_id == token_id,
        RefreshToken.revoked_at == None,  # noqa: E711
        RefreshToken.expires_at > now,
    )


async def revoke(token_id: str) -> bool:
    """refresh 세션을 폐기 처리한다.

    Args:
        token_id: 폐기할 refresh JWT의 jti 값.

    Returns:
        bool: 폐기 대상 세션이 있으면 True, 없으면 False.
    """

    # refresh 세션을 token_id로 조회해 로그아웃 대상인지 확인한다
    refresh_token = await RefreshToken.find_one(RefreshToken.token_id == token_id)
    if refresh_token is None:
        return False

    refresh_token.revoked_at = datetime.now(UTC)

    # 변경된 revoked_at 값을 MongoDB에 저장한다
    await refresh_token.save()
    return True
