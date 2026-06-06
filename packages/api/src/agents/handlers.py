from fastapi import APIRouter, Depends

from src.agents.dependencies import get_target_role_service
from src.agents.models import AgentIdentity
from src.agents.schemas import ListRolesResponse, GetMeResponse
from src.agents.services import TargetRoleService
from src.dependencies import verify_token, get_current_agent

router = APIRouter(prefix="/agents", tags=["agents"], dependencies=[Depends(verify_token)])


@router.get("/roles", response_model=list[ListRolesResponse])
async def list_roles(
    service: TargetRoleService = Depends(get_target_role_service)
):
    roles = await service.get_all_roles()
    return roles


@router.get("/me", response_model=GetMeResponse)
async def get_me(
    current_agent: AgentIdentity = Depends(get_current_agent)
):
    return current_agent
