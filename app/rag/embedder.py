"""
embedder 모듈은 텍스트를 벡터 임베딩으로 변환하는 인터페이스를 정의한다.
실제 임베딩 모델과 OpenAI Embeddings 연동은 추후 구현한다.
"""


async def embed(text: str) -> list[float]:
    """텍스트를 임베딩 벡터로 변환한다.

    Args:
        text: 임베딩할 원문 텍스트.

    Returns:
        list[float]: 벡터 검색에 사용할 임베딩 값.

    Raises:
        NotImplementedError: 실제 임베딩 구현이 아직 없을 때 발생한다.
    """

    # TODO: 추후 구현 - OpenAI Embeddings 또는 사내 임베딩 모델 연동
    raise NotImplementedError
