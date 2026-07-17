from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status

from forkflux_api.agents.dependencies import get_agent_identity_roles_service
from forkflux_api.agents.models import AgentIdentity, TargetRole
from forkflux_api.agents.services import AgentIdentityRoleService
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
    validate_target_role_claim_next,
    validate_target_role_query_param,
)
from forkflux_api.jobs.dto import HandoffJobFilterParams
from forkflux_api.jobs.exceptions import HandoffJobConflictError, HandoffJobNotFoundError
from forkflux_api.jobs.helpers import handoff_job_to_response_model
from forkflux_api.jobs.schemas import (
    HandoffJobChangeStatusRequest,
    HandoffJobChangeStatusResponse,
    HandoffJobClaimNextRequest,
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
    status: list[JobStatusEnum] | None = Query(default=None),
    order: list[JobListOrderEnum] = Query(default=[JobListOrderEnum.CREATED_AT_ASC]),
    target_role_key: TargetRole = Depends(validate_target_role_query_param),
    my_roles_only: bool = True,
    job_service: HandoffJobService = Depends(get_handoff_job_service),
    current_agent: AgentIdentity = Depends(get_current_agent),
    agent_identity_role_service: AgentIdentityRoleService = Depends(get_agent_identity_roles_service),
):
    statuses = status or []
    list_current_role_ids = await agent_identity_role_service.list_role_ids(agent_identity_id=current_agent.id)
    target_role_ids = list_current_role_ids if my_roles_only else [target_role_key.id] if target_role_key else []
    jobs = await job_service.list_jobs(
        HandoffJobFilterParams(limit=limit, statuses=statuses, target_role_ids=target_role_ids, order=order)
    )
    return [
        HandoffJobListItem(
            id=x.job_details.id,
            parent_job_id=x.job_details.parent_job_id,
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


@router.post("/claim-next", status_code=http_status.HTTP_201_CREATED, response_model=HandoffJobWithArtifactsItem)
async def claim_next_job(
    data: HandoffJobClaimNextRequest,
    valid_target_role: TargetRole = Depends(validate_target_role_claim_next),
    job_service: HandoffJobService = Depends(get_handoff_job_service),
    current_agent: AgentIdentity = Depends(get_current_agent),
    agent_identity_role_service: AgentIdentityRoleService = Depends(get_agent_identity_roles_service),
):
    agent_role_ids = await agent_identity_role_service.list_role_ids(agent_identity_id=current_agent.id)

    jobs = await job_service.list_jobs(
        HandoffJobFilterParams(
            limit=1,
            statuses=[JobStatusEnum.PUBLISHED],
            target_role_ids=[valid_target_role.id],
            order=[JobListOrderEnum.PRIORITY_DESC, JobListOrderEnum.CREATED_AT_ASC],
        )
    )

    if not jobs:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="No published jobs available for the given target role.",
        )

    job_id = jobs[0].job_details.id

    try:
        await job_service.claim_job(job_id=job_id, agent_id=current_agent.id, agent_role_ids=agent_role_ids)
    except (HandoffJobNotFoundError, HandoffJobConflictError) as err:
        raise HandoffJobClaimValidationError(field_name="job_id", value=job_id, loc="body", detail=err.msg)

    entity = await job_service.get_job_with_artifacts(job_id)
    return handoff_job_to_response_model(entity=entity)


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
    agent_identity_role_service: AgentIdentityRoleService = Depends(get_agent_identity_roles_service),
):
    try:
        agent_role_ids = await agent_identity_role_service.list_role_ids(agent_identity_id=current_agent.id)
        await job_service.claim_job(job_id=job_id, agent_id=current_agent.id, agent_role_ids=agent_role_ids)
    except (HandoffJobNotFoundError, HandoffJobConflictError) as err:
        raise HandoffJobClaimValidationError(field_name="job_id", value=job_id, loc="path", detail=err.msg)

    entity = await job_service.get_job_with_artifacts(job_id)
    return handoff_job_to_response_model(entity=entity)


@router.post(
    "/{job_id}/status",
    status_code=http_status.HTTP_200_OK,
    response_model=HandoffJobChangeStatusResponse,
)
async def change_job_status(
    job_id: int,
    data: HandoffJobChangeStatusRequest,
    job_service: HandoffJobService = Depends(get_handoff_job_service),
    current_agent: AgentIdentity = Depends(get_current_agent),
):
    try:
        previous_status, new_status = await job_service.change_job_status(
            job_id, data.status, current_agent.id, data.failure_reason
        )
    except HandoffJobNotFoundError:
        raise HandoffJobIdentityValidationError(field_name="job_id", value=job_id, loc="path")
    except HandoffJobConflictError:
        raise HandoffJobStatusValidationError(field_name="status", value=data.status, loc="body")

    return {"job_id": job_id, "previous_status": previous_status, "new_status": new_status}
