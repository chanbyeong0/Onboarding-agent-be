"""user_learning_progress CRUD 모듈은 사용자별 강의 진행도 저장과 조회를 담당한다."""

from datetime import UTC, datetime

from beanie import PydanticObjectId

from app.models.user_learning_progress import UserLearningProgress


async def upsert_page_view(
    *,
    user_id: str,
    session_id: str,
    document_id: str,
    page_number: int,
    total_pages: int,
    study_seconds_delta: int = 0,
) -> UserLearningProgress:
    """페이지 열람 기록을 사용자 진행도에 반영한다."""

    now = datetime.now(UTC)
    progress = await UserLearningProgress.find_one(
        UserLearningProgress.user_id == PydanticObjectId(user_id),
        UserLearningProgress.session_id == PydanticObjectId(session_id),
        UserLearningProgress.document_id == PydanticObjectId(document_id),
    )

    normalized_page = max(1, page_number)
    normalized_total = max(total_pages, normalized_page)
    normalized_delta = max(0, study_seconds_delta)

    if progress is None:
        progress = UserLearningProgress(
            user_id=PydanticObjectId(user_id),
            session_id=PydanticObjectId(session_id),
            document_id=PydanticObjectId(document_id),
            viewed_pages=[normalized_page],
            last_page_number=normalized_page,
            total_pages=normalized_total,
            study_seconds=normalized_delta,
            completed_at=now if normalized_total <= 1 else None,
            updated_at=now,
        )
        return await progress.insert()

    viewed_pages = set(progress.viewed_pages)
    viewed_pages.add(normalized_page)
    progress.viewed_pages = sorted(viewed_pages)
    progress.last_page_number = normalized_page
    progress.total_pages = max(progress.total_pages, normalized_total)
    progress.study_seconds += normalized_delta
    progress.updated_at = now
    if progress.total_pages > 0 and len(progress.viewed_pages) >= progress.total_pages and progress.completed_at is None:
        progress.completed_at = now
    return await progress.save()


async def list_by_user(user_id: str) -> list[UserLearningProgress]:
    """사용자의 전체 학습 진행도를 조회한다."""

    return await UserLearningProgress.find(UserLearningProgress.user_id == PydanticObjectId(user_id)).to_list()


async def list_by_user_and_sessions(user_id: str, session_ids: list[str]) -> list[UserLearningProgress]:
    """사용자의 여러 강의 세션 진행도를 조회한다."""

    if not session_ids:
        return []
    object_session_ids = {PydanticObjectId(session_id) for session_id in session_ids}
    progresses = await UserLearningProgress.find(UserLearningProgress.user_id == PydanticObjectId(user_id)).to_list()
    return [progress for progress in progresses if progress.session_id in object_session_ids]


async def delete_by_session(session_id: str) -> None:
    """삭제된 강의 세션에 연결된 진행도를 정리한다."""

    progresses = await UserLearningProgress.find(UserLearningProgress.session_id == PydanticObjectId(session_id)).to_list()
    for progress in progresses:
        await progress.delete()
