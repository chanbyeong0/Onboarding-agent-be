"""seed 모듈은 해커톤 MVP 실행에 필요한 기본 데이터를 보장한다."""

from app.core.security import hash_password
from app.crud import user as user_crud
from app.models.user import User

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin123"
ADMIN_NAME = "관리자"


async def ensure_admin_user() -> None:
    """기본 관리자 계정을 생성하거나 관리자 역할을 보정한다."""

    existing_user = await user_crud.get_by_email(ADMIN_EMAIL)
    if existing_user is None:
        await User(
            email=ADMIN_EMAIL,
            password=hash_password(ADMIN_PASSWORD),
            name=ADMIN_NAME,
            role="admin",
        ).insert()
        return

    if existing_user.role != "admin":
        existing_user.role = "admin"
        await existing_user.save()
