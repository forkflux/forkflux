from fastapi import APIRouter, Depends, Query
from fastapi import status as http_status
from src.agents.models import AgentIdentity, TargetRole
from src.dependencies import get_current_agent, verify_token
from src.jobs.constants import JobPriorityEnum, JobStatusEnum
from src.jobs.dependencies import (
    get_handoff_job_service,
    validate_parent_job,
    validate_target_role,
    validate_target_role_query_param,
)
from src.jobs.schemas import (
    HandoffJobCreateRequest,
    HandoffJobCreateResponse,
    HandoffJobFilterParams,
    HandoffJobListItem,
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
    limit: int = Query(50, ge=1, le=100),
    status: JobStatusEnum | None = None,
    target_role_key: str | None = Depends(validate_target_role_query_param),
    job_service: HandoffJobService = Depends(get_handoff_job_service),
):
    jobs = await job_service.list_jobs(
        HandoffJobFilterParams(limit=limit, status=status, target_role_key=target_role_key)
    )
    return [
        HandoffJobListItem(
            id=x.job.id,
            summary=x.job.summary,
            status=x.job.status,
            priority=JobPriorityEnum(x.job.priority),
            source_agent_label=x.source_agent_label,
            assignee_agent_label=x.assignee_agent_label,
            target_role_key=x.target_role_key,
            created_at=x.job.created_at,
        )
        for x in jobs
    ]
