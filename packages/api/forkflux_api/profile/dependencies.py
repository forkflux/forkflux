from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from forkflux_api.database import get_session
from forkflux_api.profile.repositories import ProfileRepository
from forkflux_api.profile.services import ProfileService


def get_trace_id(request: Request) -> str:
    return request.state.trace_id


def get_profile_repo(
    session: AsyncSession = Depends(get_session), trace_id: str = Depends(get_trace_id)
) -> ProfileRepository:
    return ProfileRepository(session=session, trace_id=trace_id)


def get_profile_service(
    repository: ProfileRepository = Depends(get_profile_repo), trace_id: str = Depends(get_trace_id)
) -> ProfileService:
    return ProfileService(profile_repo=repository, trace_id=trace_id)
