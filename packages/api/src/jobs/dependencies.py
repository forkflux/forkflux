from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from src.agents.dependencies import get_target_role_service
from src.agents.exceptions import TargetRoleNotFoundError
from src.agents.models import TargetRole
from src.agents.services import TargetRoleService
from src.database import get_session
from src.jobs.api_exceptions import ParentJobValidationError, TargetRoleValidationError
from src.jobs.dto import HandoffJobItem
from src.jobs.exceptions import HandoffJobNotFoundError
from src.jobs.repositories import HandoffJobRepository, JobArtifactRepository, JobEventRepository
from src.jobs.schemas import HandoffJobCreateRequest
from src.jobs.services import HandoffJobService


def get_trace_id(request: Request) -> str:
    return request.state.trace_id


async def get_handoff_job_repo(
    session: AsyncSession = Depends(get_session), trace_id: str = Depends(get_trace_id)
) -> HandoffJobRepository:
    return HandoffJobRepository(session=session, trace_id=trace_id)


async def get_job_artifact_repo(
    session: AsyncSession = Depends(get_session), trace_id: str = Depends(get_trace_id)
) -> JobArtifactRepository:
    return JobArtifactRepository(session=session, trace_id=trace_id)


async def get_job_event_repo(
    session: AsyncSession = Depends(get_session), trace_id: str = Depends(get_trace_id)
) -> JobEventRepository:
    return JobEventRepository(session=session, trace_id=trace_id)


def get_handoff_job_service(
    repository: HandoffJobRepository = Depends(get_handoff_job_repo),
    job_artifact_repo: JobArtifactRepository = Depends(get_job_artifact_repo),
    job_event_repo: JobEventRepository = Depends(get_job_event_repo),
    trace_id: str = Depends(get_trace_id),
) -> HandoffJobService:
    return HandoffJobService(
        handoff_job_repo=repository,
        job_artifact_repo=job_artifact_repo,
        job_event_repo=job_event_repo,
        trace_id=trace_id,
    )


async def validate_parent_job(
    job_data: HandoffJobCreateRequest, service: HandoffJobService = Depends(get_handoff_job_service)
) -> HandoffJobItem | None:
    if job_data.parent_job_id is None:
        return None

    try:
        parent_job = await service.get_job(job_id=job_data.parent_job_id)
        return parent_job
    except HandoffJobNotFoundError:
        raise ParentJobValidationError(field_name="parent_job_id", value=job_data.parent_job_id)


async def validate_target_role(
    job_data: HandoffJobCreateRequest, service: TargetRoleService = Depends(get_target_role_service)
) -> TargetRole:
    try:
        target_role = await service.get_by_role_key(role_key=job_data.target_role_key)
        return target_role
    except TargetRoleNotFoundError:
        raise TargetRoleValidationError(field_name="target_role_key", value=job_data.target_role_key)


async def validate_target_role_query_param(
    target_role_key: str | None = None, service: TargetRoleService = Depends(get_target_role_service)
) -> TargetRole | None:
    if target_role_key is None:
        return None

    try:
        role = await service.get_by_role_key(role_key=target_role_key)
        return role
    except TargetRoleNotFoundError:
        raise TargetRoleValidationError(field_name="target_role_key", value=target_role_key, loc="query")
