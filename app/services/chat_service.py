"""chat_service 모듈은 채팅 응답 생성과 저장 흐름을 담당한다."""

from app.crud import chat_message as chat_message_crud
from app.crud import document as document_crud
from app.crud import lecture_session as lecture_session_crud
from app.schemas.chat import ChatRequest
from app.services import agent_service


class ChatResourceNotFoundError(RuntimeError):
    """채팅 요청에 포함된 세션 또는 문서를 찾지 못했을 때 발생한다."""


async def generate_answer(chat_request: ChatRequest, *, user_id: str) -> str:
    """채팅 요청을 검증하고 AI 답변을 생성한 뒤 학습 기록으로 저장한다."""

    if chat_request.session_id:
        session = await lecture_session_crud.get_by_id(chat_request.session_id)
        if session is None:
            raise ChatResourceNotFoundError("강의 세션을 찾을 수 없습니다.")

    if chat_request.document_id:
        document = await document_crud.get_by_id(chat_request.document_id)
        if document is None:
            raise ChatResourceNotFoundError("문서를 찾을 수 없습니다.")

    answer = await agent_service.generate_chat_answer(chat_request)
    if chat_request.session_id:
        await chat_message_crud.create(
            session_id=chat_request.session_id,
            user_id=user_id,
            message=chat_request.message,
            answer=answer,
            document_id=chat_request.document_id,
            page_number=chat_request.page_number,
        )
    return answer
