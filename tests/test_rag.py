"""
test_rag 모듈은 RAG 인터페이스가 아직 구현되지 않았음을 명시적으로 검증한다.
추후 실제 구현이 들어오면 이 테스트를 검색 결과 검증으로 교체한다.
"""

import pytest

from app.rag.embedder import embed
from app.rag.pipeline import index_chunks, run_pipeline
from app.rag.retriever import retrieve


@pytest.mark.asyncio
async def test_rag_stubs_raise_not_implemented() -> None:
    """RAG TODO 함수들이 NotImplementedError를 발생시키는지 확인한다."""

    # 임베딩 인터페이스가 아직 실제 모델에 연결되지 않았음을 확인한다
    with pytest.raises(NotImplementedError):
        await embed("테스트")

    # 검색 인터페이스가 아직 MongoDB 벡터 검색에 연결되지 않았음을 확인한다
    with pytest.raises(NotImplementedError):
        await retrieve("테스트")

    # RAG 파이프라인이 아직 구현되지 않았음을 확인한다
    with pytest.raises(NotImplementedError):
        await run_pipeline("테스트")

    # 색인 인터페이스가 아직 구현되지 않았음을 확인한다
    with pytest.raises(NotImplementedError):
        await index_chunks([{"text": "테스트"}], metadata={"document_id": "doc"})
