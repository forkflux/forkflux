from fastapi import APIRouter, Depends

from forkflux_api.agents.dependencies import get_target_role_service
from forkflux_api.agents.models import AgentIdentity
from forkflux_api.agents.schemas import GetMeResponse, ListRolesResponse
from forkflux_api.agents.services import TargetRoleService
from forkflux_api.dependencies import get_current_agent, verify_token

router = APIRouter(prefix="/agents", tags=["agents"], dependencies=[Depends(verify_token)])


@router.get("/roles", response_model=list[ListRolesResponse])
async def list_roles(service: TargetRoleService = Depends(get_target_role_service)):
    roles = await service.get_all_roles()
    return roles


@router.get("/me", response_model=GetMeResponse)
async def get_me(current_agent: AgentIdentity = Depends(get_current_agent)):
    return current_agent
