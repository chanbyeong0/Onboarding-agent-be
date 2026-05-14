"""
retriever 모듈은 사용자 질문과 관련된 문서 청크를 검색하는 인터페이스를 정의한다.
MongoDB 벡터 검색 쿼리와 랭킹 로직은 추후 구현한다.
"""


async def retrieve(query: str, top_k: int = 5) -> list[str]:
    """질문과 관련된 상위 문서 청크를 검색한다.

    Args:
        query: 사용자의 질문 또는 검색 문장.
        top_k: 반환할 관련 청크 개수.

    Returns:
        list[str]: 관련 문서 청크 텍스트 목록.

    Raises:
        NotImplementedError: 실제 검색 구현이 아직 없을 때 발생한다.
    """

    # TODO: 추후 구현 - MongoDB Atlas Vector Search 기반 검색 연결
    raise NotImplementedError
