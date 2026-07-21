from unittest.mock import AsyncMock, Mock

import pytest
from forkflux_api.profile.dto import ProfileCreate
from forkflux_api.profile.exceptions import ProfileAlreadyExistsError, ProfileNotFoundError
from forkflux_api.profile.services import ProfileService


async def test_profile_service_init_sets_repository_and_logger() -> None:
    repository = Mock()
    repository.get = AsyncMock(return_value=True)

    service = ProfileService(profile_repo=repository, trace_id="trace-123")

    assert service._profile_repo is repository
    assert service._logger is not None


async def test_profile_service_get_profile_delegates_and_returns_is_onboarded() -> None:
    repository = Mock()
    repository.get = AsyncMock(return_value=True)
    service = ProfileService(profile_repo=repository, trace_id="trace-123")

    is_onboarded = await service.get_profile()

    repository.get.assert_awaited_once_with()
    assert is_onboarded is True


async def test_profile_service_get_profile_returns_false_when_not_onboarded() -> None:
    repository = Mock()
    repository.get = AsyncMock(return_value=False)
    service = ProfileService(profile_repo=repository, trace_id="trace-123")

    is_onboarded = await service.get_profile()

    repository.get.assert_awaited_once_with()
    assert is_onboarded is False


async def test_profile_service_get_profile_propagates_not_found() -> None:
    repository = Mock()
    repository.get = AsyncMock(side_effect=ProfileNotFoundError)
    service = ProfileService(profile_repo=repository, trace_id="trace-123")

    with pytest.raises(ProfileNotFoundError):
        await service.get_profile()


async def test_profile_service_create_delegates_and_returns_profile_when_not_exists() -> None:
    created_profile = Mock()
    repository = Mock()
    repository.exists = AsyncMock(return_value=False)
    repository.create = AsyncMock(return_value=created_profile)
    service = ProfileService(profile_repo=repository, trace_id="trace-123")

    dto = ProfileCreate(is_onboarded=True)
    result = await service.create(dto)

    repository.exists.assert_awaited_once_with()
    repository.create.assert_awaited_once_with(dto)
    assert result is created_profile


async def test_profile_service_create_raises_already_exists_when_exists_returns_true() -> None:
    repository = Mock()
    repository.exists = AsyncMock(return_value=True)
    repository.create = AsyncMock()
    service = ProfileService(profile_repo=repository, trace_id="trace-123")

    dto = ProfileCreate(is_onboarded=True)
    with pytest.raises(ProfileAlreadyExistsError):
        await service.create(dto)

    repository.create.assert_not_awaited()
