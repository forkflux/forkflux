import structlog

from forkflux_api.profile.dto import ProfileCreate
from forkflux_api.profile.exceptions import ProfileAlreadyExistsError
from forkflux_api.profile.models import Profile
from forkflux_api.profile.repositories import ProfileRepository


class ProfileService:
    def __init__(self, profile_repo: ProfileRepository, trace_id: str) -> None:
        self._logger = structlog.get_logger().bind(cls=self.__class__.__name__, trace_id=trace_id)
        self._profile_repo = profile_repo

    async def get_profile(self) -> bool:
        log = self._logger.bind(method="get_profile")
        log.info("operation_started")

        is_onboarded = await self._profile_repo.get()

        log.info("operation_completed", is_onboarded=is_onboarded)
        return is_onboarded

    async def create(self, dto: ProfileCreate) -> Profile:
        log = self._logger.bind(method="create", is_onboarded=dto.is_onboarded)
        log.info("operation_started")

        profile_exists = await self._profile_repo.exists()
        if profile_exists:
            log.info("profile_already_exists")
            raise ProfileAlreadyExistsError

        profile = await self._profile_repo.create(dto)

        log.info("operation_completed", profile_id=profile.id)
        return profile
