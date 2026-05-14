"""
session 모듈은 MongoDB 클라이언트와 Beanie 초기화를 담당한다.
관계형 DB 세션 대신 애플리케이션 lifespan에서 한 번 초기화되는 Mongo 연결을 제공한다.
"""

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings
from app.models.checkpoint import Checkpoint
from app.models.document import DocumentModel
from app.models.refresh_token import RefreshToken
from app.models.user import User

mongo_client: AsyncIOMotorClient | None = None


def get_mongo_client() -> AsyncIOMotorClient:
    """공유 MongoDB 클라이언트를 반환한다.

    Returns:
        AsyncIOMotorClient: 애플리케이션 전체에서 재사용할 비동기 MongoDB 클라이언트.
    """

    global mongo_client
    if mongo_client is None:
        # 설정의 MongoDB URL로 비동기 클라이언트를 지연 생성한다
        mongo_client = AsyncIOMotorClient(settings.mongodb_url)
    return mongo_client


def get_database() -> AsyncIOMotorDatabase:
    """설정된 MongoDB 데이터베이스 객체를 반환한다.

    Returns:
        AsyncIOMotorDatabase: Beanie와 벡터 컬렉션이 사용할 데이터베이스 객체.
    """

    # 공유 클라이언트에서 서비스 전용 데이터베이스를 선택한다
    return get_mongo_client()[settings.mongodb_db_name]


async def init_db() -> None:
    """Beanie에 문서 모델을 등록하고 MongoDB 연결을 초기화한다."""

    # Beanie가 인증/문서/체크포인트 컬렉션을 비동기 모델로 사용할 수 있게 등록한다
    await init_beanie(
        database=get_database(),
        document_models=[User, DocumentModel, Checkpoint, RefreshToken],
    )


async def close_db() -> None:
    """애플리케이션 종료 시 MongoDB 클라이언트를 닫는다."""

    global mongo_client
    if mongo_client is not None:
        # Motor 클라이언트의 소켓 리소스를 명시적으로 정리한다
        mongo_client.close()
        mongo_client = None
