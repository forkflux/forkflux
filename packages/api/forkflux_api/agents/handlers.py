from fastapi import APIRouter, Depends

from forkflux_api.agents.dependencies import get_agent_identity_roles_service, get_target_role_service
from forkflux_api.agents.models import AgentIdentity
from forkflux_api.agents.schemas import GetMeResponse, ListRolesResponse
from forkflux_api.agents.services import AgentIdentityRoleService, TargetRoleService
from forkflux_api.dependencies import get_current_agent, verify_token

router = APIRouter(prefix="/agents", tags=["agents"], dependencies=[Depends(verify_token)])


@router.get("/roles", response_model=list[ListRolesResponse])
async def list_roles(service: TargetRoleService = Depends(get_target_role_service)):
    roles = await service.get_all_roles()
    return roles


@router.get("/me", response_model=GetMeResponse)
async def get_me(current_agent: AgentIdentity = Depends(get_current_agent)):
    return current_agent


@router.get("/me/roles", response_model=list[ListRolesResponse])
async def list_my_roles(
    current_agent: AgentIdentity = Depends(get_current_agent),
    agent_identity_role_service: AgentIdentityRoleService = Depends(get_agent_identity_roles_service),
    target_role_service: TargetRoleService = Depends(get_target_role_service),
):
    role_ids = await agent_identity_role_service.list_role_ids(agent_identity_id=current_agent.id)
    roles = await target_role_service.get_roles_by_ids(role_ids)
    return roles
