import structlog
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from forkflux_api.profile.dto import ProfileCreate
from forkflux_api.profile.exceptions import ProfileNotFoundError
from forkflux_api.profile.models import Profile


class ProfileRepository:
    def __init__(self, session: AsyncSession, trace_id: str) -> None:
        self._session = session
        self._logger = structlog.get_logger().bind(cls=self.__class__.__name__, trace_id=trace_id)

    async def get(self) -> bool:
        log = self._logger.bind(method="get")
        log.info("operation_started")

        result = await self._session.execute(select(Profile).order_by(Profile.id.asc()).limit(1))
        profile = result.scalar_one_or_none()
        if profile is None:
            log.info("profile_not_found")
            raise ProfileNotFoundError

        log.info("operation_completed", profile_id=profile.id, is_onboarded=profile.is_onboarded)
        return profile.is_onboarded

    async def exists(self) -> bool:
        log = self._logger.bind(method="exists")
        result = await self._session.execute(select(exists().select_from(Profile)))
        profile_exists = result.scalar_one()

        if profile_exists:
            log.info("profile_exists_hit")
        else:
            log.info("profile_exists_miss")

        return profile_exists

    async def create(self, dto: ProfileCreate) -> Profile:
        log = self._logger.bind(method="create", is_onboarded=dto.is_onboarded)
        log.info("operation_started")

        profile = Profile(is_onboarded=dto.is_onboarded)
        self._session.add(profile)
        await self._session.flush()

        log.info("operation_completed", profile_id=profile.id)
        return profile
