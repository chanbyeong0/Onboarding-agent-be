"""
user CRUD 모듈은 사용자 조회, 생성, 인증을 위한 Beanie 접근 함수를 제공한다.
비밀번호 검증은 보안 모듈에 위임하고, 이 모듈은 저장소 접근을 담당한다.
"""

from beanie import PydanticObjectId

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserCreate


async def get_by_email(email: str) -> User | None:
    """이메일로 사용자를 조회한다.

    Args:
        email: 로그인 식별자로 사용하는 이메일.

    Returns:
        User | None: 사용자가 있으면 User 문서, 없으면 None.
    """

    # 이메일 고유 인덱스를 사용해 사용자 문서를 조회한다
    return await User.find_one(User.email == email)


async def get_by_id(user_id: str) -> User | None:
    """문자열 ObjectId로 사용자를 조회한다.

    Args:
        user_id: JWT subject에 저장된 사용자 ObjectId 문자열.

    Returns:
        User | None: 사용자가 있으면 User 문서, 없거나 id가 잘못되면 None.
    """

    try:
        object_id = PydanticObjectId(user_id)
    except Exception:
        return None

    # ObjectId 기본 키로 사용자 문서를 조회한다
    return await User.get(object_id)


async def create(user_in: UserCreate) -> User:
    """회원가입 요청으로 새 사용자를 생성한다.

    Args:
        user_in: 이메일, 비밀번호, 이름을 담은 회원가입 요청.

    Returns:
        User: MongoDB에 저장된 사용자 문서.
    """

    # 평문 비밀번호를 저장 가능한 bcrypt 해시로 변환한다
    hashed_password = hash_password(user_in.password)
    user = User(email=user_in.email, password=hashed_password, name=user_in.name)

    # Beanie insert로 사용자 문서를 users 컬렉션에 저장한다
    return await user.insert()


async def authenticate(email: str, password: str) -> User | None:
    """이메일과 비밀번호로 사용자를 인증한다.

    Args:
        email: 로그인 요청 이메일.
        password: 로그인 요청 평문 비밀번호.

    Returns:
        User | None: 인증에 성공하면 User 문서, 실패하면 None.
    """

    # 이메일로 먼저 사용자 문서를 찾아 비밀번호 검증 대상을 얻는다
    user = await get_by_email(email)
    if user is None:
        return None

    # 보안 모듈에 bcrypt 해시 검증을 위임한다
    if not verify_password(password, user.password):
        return None
    return user
