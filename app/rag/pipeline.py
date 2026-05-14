"""
pipeline 모듈은 RAG 색인과 검색 흐름을 묶는 인터페이스를 정의한다.
현재는 함수 시그니처만 제공하고 실제 구현은 TODO로 남겨둔다.
"""

from typing import Any


async def run_pipeline(query: str) -> list[str]:
    """질문을 받아 RAG 검색 컨텍스트를 반환한다.

    Args:
        query: 사용자 질문.

    Returns:
        list[str]: LLM 프롬프트에 주입할 관련 컨텍스트 목록.

    Raises:
        NotImplementedError: 실제 RAG 파이프라인 구현이 아직 없을 때 발생한다.
    """

    # TODO: 추후 구현 - 임베딩 생성, 벡터 검색, 컨텍스트 정렬을 연결
    raise NotImplementedError


async def index_chunks(chunks: list[dict[str, Any]], metadata: dict[str, Any] | None = None) -> None:
    """문서 청크를 벡터 저장소에 색인한다.

    Args:
        chunks: 텍스트와 페이지 메타데이터가 포함된 청크 목록.
        metadata: 문서 단위로 공통 적용할 추가 메타데이터.

    Raises:
        NotImplementedError: 실제 색인 구현이 아직 없을 때 발생한다.
    """

    # TODO: 추후 구현 - 청크 임베딩 생성 후 MongoDB 벡터 컬렉션에 저장
    raise NotImplementedError
