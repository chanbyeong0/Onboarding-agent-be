"""chat_message CRUD 모듈은 강의 세션 AI 질문 기록을 저장하고 조회한다."""

from beanie import PydanticObjectId

from app.models.chat_message import ChatMessage


async def create(
    *,
    session_id: str,
    user_id: str,
    message: str,
    answer: str | None = None,
    document_id: str | None = None,
    page_number: int | None = None,
) -> ChatMessage:
    """강의 세션 질문 기록을 생성한다."""

    chat_message = ChatMessage(
        session_id=PydanticObjectId(session_id),
        user_id=PydanticObjectId(user_id),
        document_id=PydanticObjectId(document_id) if document_id else None,
        page_number=page_number,
        message=message,
        answer=answer,
    )
    return await chat_message.insert()


async def count_by_user(user_id: str) -> int:
    """사용자가 남긴 AI 질문 수를 계산한다."""

    return await ChatMessage.find(ChatMessage.user_id == PydanticObjectId(user_id)).count()


async def list_by_user_and_session(user_id: str, session_id: str) -> list[ChatMessage]:
    """사용자의 특정 강의 세션 질문 기록을 최신순으로 조회한다."""

    return (
        await ChatMessage.find(
            ChatMessage.user_id == PydanticObjectId(user_id),
            ChatMessage.session_id == PydanticObjectId(session_id),
        )
        .sort("-created_at")
        .to_list()
    )


async def delete_by_session(session_id: str) -> None:
    """삭제된 강의 세션에 연결된 AI 질문 기록을 정리한다."""

    messages = await ChatMessage.find(ChatMessage.session_id == PydanticObjectId(session_id)).to_list()
    for message in messages:
        await message.delete()
