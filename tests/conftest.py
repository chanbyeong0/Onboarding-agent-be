"""
conftest 모듈은 테스트용 FastAPI 클라이언트와 인메모리 MongoDB를 준비한다.
실제 MongoDB와 OpenAI API를 호출하지 않도록 Beanie와 서비스 계층을 테스트용으로 초기화한다.
"""

import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from beanie import init_beanie
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017")
os.environ.setdefault("MONGODB_DB_NAME", "test_onboarding")
os.environ.setdefault("UPLOAD_DIR", "./test_uploads")

from app.core.security import create_access_token, hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.models.checkpoint import Checkpoint  # noqa: E402
from app.models.chat_message import ChatMessage  # noqa: E402
from app.models.document import DocumentModel  # noqa: E402
from app.models.document_page import DocumentPage  # noqa: E402
from app.models.exam_attempt import ExamAttempt  # noqa: E402
from app.models.lecture_session import LectureSession  # noqa: E402
from app.models.page_explanation import PageExplanation  # noqa: E402
from app.models.refresh_token import RefreshToken  # noqa: E402
from app.models.user import User  # noqa: E402


@pytest_asyncio.fixture(autouse=True)
async def init_test_database() -> AsyncIterator[None]:
    """각 테스트마다 Beanie를 인메모리 MongoDB에 연결한다.

    Yields:
        None: 테스트 실행 구간.
    """

    # mongomock 기반 Motor 클라이언트로 외부 MongoDB 의존성을 제거한다
    client = AsyncMongoMockClient()

    # Beanie 문서 모델을 테스트 데이터베이스에 등록한다
    await init_beanie(
        database=client["test_onboarding"],
        document_models=[
            User,
            DocumentModel,
            DocumentPage,
            LectureSession,
            Checkpoint,
            ChatMessage,
            PageExplanation,
            ExamAttempt,
            RefreshToken,
        ],
    )
    yield

    # 테스트 간 데이터 오염을 막기 위해 Beanie 모델 단위로 컬렉션을 정리한다
    await User.delete_all()
    await DocumentModel.delete_all()
    await DocumentPage.delete_all()
    await LectureSession.delete_all()
    await Checkpoint.delete_all()
    await ChatMessage.delete_all()
    await PageExplanation.delete_all()
    await ExamAttempt.delete_all()
    await RefreshToken.delete_all()


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """FastAPI ASGI 앱을 호출하는 비동기 테스트 클라이언트를 제공한다.

    Yields:
        AsyncClient: HTTP 요청을 보낼 수 있는 테스트 클라이언트.
    """

    # ASGITransport로 네트워크 없이 FastAPI 앱을 직접 호출한다
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


@pytest_asyncio.fixture
async def auth_headers() -> dict[str, str]:
    """인증이 필요한 테스트에 사용할 Bearer 헤더를 생성한다.

    Returns:
        dict[str, str]: Authorization 헤더.
    """

    # 테스트 사용자 비밀번호를 bcrypt로 해싱해 실제 로그인 데이터와 같은 형태로 저장한다
    password = hash_password("password123")
    user = User(email="tester@example.com", password=password, name="Tester")

    # 테스트 사용자를 인메모리 MongoDB에 저장한다
    await user.insert()

    # 테스트 사용자 ObjectId를 subject로 담은 JWT를 발급한다
    token = create_access_token(str(user.id))
    return {"Authorization": f"Bearer {token}"}
