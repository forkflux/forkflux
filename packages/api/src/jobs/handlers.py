from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from src.agents.models import AgentIdentity, TargetRole
from src.dependencies import get_current_agent, verify_token
from src.jobs.api_exceptions import (
    HandoffJobClaimValidationError,
    HandoffJobIdentityValidationError,
    HandoffJobStatusValidationError,
)
from src.jobs.constants import JobPriorityEnum, JobStatusEnum
from src.jobs.dependencies import (
    get_handoff_job_service,
    validate_parent_job,
    validate_target_role,
    validate_target_role_query_param,
)
from src.jobs.exceptions import HandoffJobConflictError, HandoffJobNotFoundError
from src.jobs.schemas import (
    HandoffJobChangeStatusRequest,
    HandoffJobCreateRequest,
    HandoffJobCreateResponse,
    HandoffJobFilterParams,
    HandoffJobListItem,
    HandoffJobWithArtifactsItem,
)
from src.jobs.schemas import (
    JobArtifact as JobArtifactItem,
)
from src.jobs.services import HandoffJobService

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
    limit: int = Query(50, ge=50, le=200),
    status: JobStatusEnum | None = None,
    target_role_key: str | None = Depends(validate_target_role_query_param),
    job_service: HandoffJobService = Depends(get_handoff_job_service),
):
    jobs = await job_service.list_jobs(
        HandoffJobFilterParams(limit=limit, status=status, target_role_key=target_role_key)
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

    job = entity["job"]
    artifacts = entity["artifacts"]

    return HandoffJobWithArtifactsItem(
        id=job.job_details.id,
        parent_job_id=job.job_details.parent_job_id,
        summary=job.job_details.summary,
        context_payload=job.job_details.context_payload,
        status=job.job_details.status,
        priority=JobPriorityEnum(job.job_details.priority),
        source_agent_label=job.source_agent_label,
        assignee_agent_label=job.assignee_agent_label,
        target_role_key=job.target_role_key,
        constraints=job.job_details.constraints,
        artifacts=[
            JobArtifactItem(
                type=artifact.artifact_type,
                uri=artifact.artifact_uri,
                checksum=artifact.artifact_checksum,
                metadata_json=artifact.metadata_json,
            )
            for artifact in artifacts
        ],
        failure_reason=job.job_details.failure_reason,
        published_at=job.job_details.published_at,
        claimed_at=job.job_details.claimed_at,
        started_at=job.job_details.started_at,
        completed_at=job.job_details.completed_at,
        failed_at=job.job_details.failed_at,
        cancelled_at=job.job_details.cancelled_at,
        expires_at=job.job_details.expires_at,
        created_at=job.job_details.created_at,
        updated_at=job.job_details.updated_at,
    )


@router.post("/{job_id}/claim", status_code=http_status.HTTP_204_NO_CONTENT)
async def claim_job(
    job_id: int,
    job_service: HandoffJobService = Depends(get_handoff_job_service),
    current_agent: AgentIdentity = Depends(get_current_agent),
):
    try:
        await job_service.claim_job(job_id, current_agent)
    except HandoffJobNotFoundError, HandoffJobConflictError:
        raise HandoffJobClaimValidationError(field_name="job_id", value=job_id, loc="path")


@router.post("/{job_id}/status", status_code=http_status.HTTP_204_NO_CONTENT)
async def change_job_status(
    job_id: int,
    data: HandoffJobChangeStatusRequest,
    job_service: HandoffJobService = Depends(get_handoff_job_service),
    current_agent: AgentIdentity = Depends(get_current_agent),
):
    try:
        await job_service.change_job_status(job_id, data.status, current_agent)
    except HandoffJobNotFoundError:
        raise HandoffJobIdentityValidationError(field_name="job_id", value=job_id, loc="path")
    except HandoffJobConflictError:
        raise HandoffJobStatusValidationError(field_name="status", value=data.status, loc="body")
