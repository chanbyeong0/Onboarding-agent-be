"""page_explanation CRUD 모듈은 페이지 해설 캐시를 조회하고 저장한다."""

from datetime import UTC, datetime

from beanie import PydanticObjectId

from app.models.page_explanation import PageExplanation


async def get_by_id(explanation_id: str) -> PageExplanation | None:
    """문자열 ObjectId로 페이지 해설 캐시를 조회한다."""

    try:
        object_id = PydanticObjectId(explanation_id)
    except Exception:
        return None
    return await PageExplanation.get(object_id)


async def get_by_scope(
    *,
    session_id: str,
    document_id: str,
    user_id: str,
    page_number: int,
) -> PageExplanation | None:
    """사용자/세션/문서/페이지 조합으로 저장된 해설을 조회한다."""

    return await PageExplanation.find_one(
        PageExplanation.session_id == PydanticObjectId(session_id),
        PageExplanation.document_id == PydanticObjectId(document_id),
        PageExplanation.user_id == PydanticObjectId(user_id),
        PageExplanation.page_number == page_number,
    )


async def upsert(
    *,
    session_id: str,
    document_id: str,
    user_id: str,
    page_number: int,
    text: str,
    audio_path: str | None,
) -> PageExplanation:
    """페이지 해설 캐시를 생성하거나 갱신한다."""

    explanation = await get_by_scope(
        session_id=session_id,
        document_id=document_id,
        user_id=user_id,
        page_number=page_number,
    )
    if explanation is None:
        explanation = PageExplanation(
            session_id=PydanticObjectId(session_id),
            document_id=PydanticObjectId(document_id),
            user_id=PydanticObjectId(user_id),
            page_number=page_number,
            text=text,
            audio_path=audio_path,
        )
        return await explanation.insert()

    explanation.text = text
    explanation.audio_path = audio_path
    explanation.updated_at = datetime.now(UTC)
    await explanation.save()
    return explanation


async def delete_by_session(session_id: str) -> None:
    """삭제된 강의 세션에 연결된 페이지 해설 캐시를 정리한다."""

    explanations = await PageExplanation.find(PageExplanation.session_id == PydanticObjectId(session_id)).to_list()
    for explanation in explanations:
        await explanation.delete()
