import pytest
from forkflux_api.profile.dto import ProfileCreate
from forkflux_api.profile.exceptions import ProfileNotFoundError
from forkflux_api.profile.repositories import ProfileRepository
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import ProfileFactory


async def test_profile_repository_init_sets_session_and_logger(db_session: AsyncSession) -> None:
    repository = ProfileRepository(trace_id="trace-123", session=db_session)

    assert repository._session is db_session
    assert repository._logger is not None


async def test_profile_repository_get_returns_is_onboarded_true(db_session: AsyncSession) -> None:
    await ProfileFactory.create(db_session, is_onboarded=True)

    repository = ProfileRepository(trace_id="trace-123", session=db_session)

    is_onboarded = await repository.get()

    assert is_onboarded is True


async def test_profile_repository_get_returns_is_onboarded_false(db_session: AsyncSession) -> None:
    await ProfileFactory.create(db_session, is_onboarded=False)

    repository = ProfileRepository(trace_id="trace-123", session=db_session)

    is_onboarded = await repository.get()

    assert is_onboarded is False


async def test_profile_repository_get_returns_first_row_ordered_by_id(db_session: AsyncSession) -> None:
    first_profile = await ProfileFactory.create(db_session, is_onboarded=True)
    await ProfileFactory.create(db_session, is_onboarded=False)

    repository = ProfileRepository(trace_id="trace-123", session=db_session)

    is_onboarded = await repository.get()

    assert is_onboarded is first_profile.is_onboarded


async def test_profile_repository_get_raises_not_found_when_table_empty(db_session: AsyncSession) -> None:
    repository = ProfileRepository(trace_id="trace-123", session=db_session)

    with pytest.raises(ProfileNotFoundError):
        await repository.get()


async def test_profile_repository_exists_returns_false_when_table_empty(db_session: AsyncSession) -> None:
    repository = ProfileRepository(trace_id="trace-123", session=db_session)

    result = await repository.exists()

    assert result is False


async def test_profile_repository_exists_returns_true_when_row_exists(db_session: AsyncSession) -> None:
    await ProfileFactory.create(db_session, is_onboarded=True)

    repository = ProfileRepository(trace_id="trace-123", session=db_session)

    result = await repository.exists()

    assert result is True


async def test_profile_repository_create_inserts_and_returns_profile_with_is_onboarded_true(
    db_session: AsyncSession,
) -> None:
    repository = ProfileRepository(trace_id="trace-123", session=db_session)

    dto = ProfileCreate(is_onboarded=True)
    profile = await repository.create(dto)

    assert profile.is_onboarded is True
    assert profile.id is not None


async def test_profile_repository_create_inserts_and_returns_profile_with_is_onboarded_false(
    db_session: AsyncSession,
) -> None:
    repository = ProfileRepository(trace_id="trace-123", session=db_session)

    dto = ProfileCreate(is_onboarded=False)
    profile = await repository.create(dto)

    assert profile.is_onboarded is False
    assert profile.id is not None
