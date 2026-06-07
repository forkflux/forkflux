from fastapi import APIRouter, Depends, status
from typing import TypedDict

from src.agents.models import TargetRole, AgentIdentity
from src.dependencies import verify_token, get_current_agent
from src.jobs.dependencies import validate_parent_job, validate_target_role, get_handoff_job_service
from src.jobs.schemas import HandoffJobCreateRequest
from src.jobs.services import HandoffJobService

router = APIRouter(prefix="/jobs", tags=["jobs"], dependencies=[Depends(verify_token)])


@router.post(
    "",
    response_model=TypedDict("CreateJobResponse", {"job_id": int}),
    status_code=status.HTTP_201_CREATED,
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
