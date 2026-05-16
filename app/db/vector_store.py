"""
vector_store 모듈은 RAG 벡터 컬렉션 접근 지점을 제공한다.
실제 MongoDB Atlas Vector Search 인덱스와 검색 로직은 추후 구현한다.
"""

from motor.motor_asyncio import AsyncIOMotorCollection

from app.db.session import get_database

VECTOR_COLLECTION_NAME = "document_vectors"


def get_vector_collection() -> AsyncIOMotorCollection:
    """문서 임베딩을 저장할 MongoDB 컬렉션을 반환한다.

    Returns:
        AsyncIOMotorCollection: 벡터 색인용 MongoDB 컬렉션.
    """

    # TODO: 추후 구현 - Atlas Vector Search 인덱스 생성과 검증 로직 추가
    return get_database()[VECTOR_COLLECTION_NAME]
