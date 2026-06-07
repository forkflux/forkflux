from fastapi import APIRouter, Depends, status
from src.agents.models import AgentIdentity, TargetRole
from src.dependencies import get_current_agent, verify_token
from src.jobs.dependencies import get_handoff_job_service, validate_parent_job, validate_target_role
from src.jobs.schemas import HandoffJobCreateRequest, HandoffJobCreateResponse
from src.jobs.services import HandoffJobService

router = APIRouter(prefix="/jobs", tags=["jobs"], dependencies=[Depends(verify_token)])


@router.post(
    "",
    response_model=HandoffJobCreateResponse,
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
