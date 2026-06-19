from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from forkflux_api.agents.models import AgentIdentity, TargetRole
from forkflux_api.dependencies import get_current_agent, verify_token
from forkflux_api.jobs.api_exceptions import (
    HandoffJobClaimValidationError,
    HandoffJobIdentityValidationError,
    HandoffJobStatusValidationError,
)
from forkflux_api.jobs.constants import JobListOrderEnum, JobPriorityEnum, JobStatusEnum
from forkflux_api.jobs.dependencies import (
    get_handoff_job_service,
    validate_parent_job,
    validate_target_role,
    validate_target_role_query_param,
)
from forkflux_api.jobs.dto import HandoffJobFilterParams
from forkflux_api.jobs.exceptions import HandoffJobConflictError, HandoffJobNotFoundError
from forkflux_api.jobs.helpers import handoff_job_to_response_model
from forkflux_api.jobs.schemas import (
    HandoffJobChangeStatusRequest,
    HandoffJobCreateRequest,
    HandoffJobCreateResponse,
    HandoffJobListItem,
    HandoffJobWithArtifactsItem,
)
from forkflux_api.jobs.services import HandoffJobService

router = APIRouter(prefix="/jobs", tags=["jobs"], dependencies=[Depends(verify_token)])


@router.post(
    "",
    response_model=HandoffJobCreateResponse,
    status_code=http_status.HTTP_201_CREATED,
    dependencies=[Depends(validate_parent_job)],
)
async def create_job(
    job_data: HandoffJobCreateRequest,
    valid_target_role: TargetRole = Depends(validate_target_role),
    current_agent: AgentIdentity = Depends(get_current_agent),
    job_service: HandoffJobService = Depends(get_handoff_job_service),
):
    job_id = await job_service.create_job(job_data, valid_target_role.id, current_agent.id)
    return {"job_id": job_id}


@router.get("", response_model=list[HandoffJobListItem])
async def list_jobs(
    limit: int = Query(50, ge=1, le=200),
    status: JobStatusEnum | None = None,
    order: list[JobListOrderEnum] = Query(default=[JobListOrderEnum.CREATED_AT_ASC]),
    target_role_key: TargetRole = Depends(validate_target_role_query_param),
    my_role_only: bool = True,
    job_service: HandoffJobService = Depends(get_handoff_job_service),
    current_agent: AgentIdentity = Depends(get_current_agent),
):
    target_role_id = current_agent.role_id if my_role_only else target_role_key.id if target_role_key else None
    jobs = await job_service.list_jobs(
        HandoffJobFilterParams(limit=limit, status=status, target_role_id=target_role_id, order=order)
    )
    return [
        HandoffJobListItem(
            id=x.job_details.id,
            summary=x.job_details.summary,
            status=x.job_details.status,
            priority=JobPriorityEnum(x.job_details.priority),
            source_agent_label=x.source_agent_label,
            assignee_agent_label=x.assignee_agent_label,
            target_role_key=x.target_role_key,
            created_at=x.job_details.created_at,
        )
        for x in jobs
    ]


@router.get("/{job_id}", response_model=HandoffJobWithArtifactsItem)
async def get_job(
    job_id: int,
    job_service: HandoffJobService = Depends(get_handoff_job_service),
):
    try:
        entity = await job_service.get_job_with_artifacts(job_id)
    except HandoffJobNotFoundError:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=HandoffJobNotFoundError.msg)

    return handoff_job_to_response_model(entity=entity)


@router.post("/{job_id}/claim", status_code=http_status.HTTP_201_CREATED, response_model=HandoffJobWithArtifactsItem)
async def claim_job(
    job_id: int,
    job_service: HandoffJobService = Depends(get_handoff_job_service),
    current_agent: AgentIdentity = Depends(get_current_agent),
):
    try:
        await job_service.claim_job(job_id, current_agent)
    except HandoffJobNotFoundError, HandoffJobConflictError:
        raise HandoffJobClaimValidationError(field_name="job_id", value=job_id, loc="path")

    entity = await job_service.get_job_with_artifacts(job_id)
    return handoff_job_to_response_model(entity=entity)


@router.post("/{job_id}/status", status_code=http_status.HTTP_204_NO_CONTENT)
async def change_job_status(
    job_id: int,
    data: HandoffJobChangeStatusRequest,
    job_service: HandoffJobService = Depends(get_handoff_job_service),
    current_agent: AgentIdentity = Depends(get_current_agent),
):
    try:
        await job_service.change_job_status(job_id, data.status, current_agent, data.failure_reason)
    except HandoffJobNotFoundError:
        raise HandoffJobIdentityValidationError(field_name="job_id", value=job_id, loc="path")
    except HandoffJobConflictError:
        raise HandoffJobStatusValidationError(field_name="status", value=data.status, loc="body")
