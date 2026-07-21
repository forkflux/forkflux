from fastapi import APIRouter, Depends
from fastapi import status as http_status

from forkflux_api.agents.api_exceptions import TargetRoleConflictValidationError, TargetRoleNotFoundValidationError
from forkflux_api.agents.dependencies import (
    get_agent_identity_service,
    get_agent_registration_use_case,
    get_target_role_service,
)
from forkflux_api.agents.dto import AgentRegistration, TargetRoleCreate
from forkflux_api.agents.exceptions import TargetRoleConflictError, TargetRoleNotFoundError
from forkflux_api.agents.services import AgentIdentityService, AgentRegistrationUseCase, TargetRoleService
from forkflux_api.agents.ui_schemas import (
    CreateAgentRequest,
    CreateAgentResponse,
    CreateRoleRequest,
    ListAgentsResponse,
    ListRolesResponse,
)

router = APIRouter(prefix="/agents", tags=["ui"])


@router.get("", response_model=list[ListAgentsResponse])
async def list_all_agents(service: AgentIdentityService = Depends(get_agent_identity_service)):
    agents = await service.list_with_roles()
    return agents


@router.post("", response_model=CreateAgentResponse, status_code=http_status.HTTP_201_CREATED)
async def create_agent(
    agent_data: CreateAgentRequest,
    use_case: AgentRegistrationUseCase = Depends(get_agent_registration_use_case),
):
    dto = AgentRegistration(
        agent_label=agent_data.agent_label,
        tool_family=agent_data.tool_family,
        target_role_ids=agent_data.target_role_ids,
    )
    try:
        result = await use_case.register_agent(dto)
    except TargetRoleNotFoundError as err:
        raise TargetRoleNotFoundValidationError(
            field_name="target_role_ids", value=agent_data.target_role_ids, loc="body", detail=err.msg
        )
    return result


@router.get("/roles", response_model=list[ListRolesResponse])
async def list_roles(service: TargetRoleService = Depends(get_target_role_service)):
    roles = await service.get_all_roles()
    return roles


@router.post("/roles", response_model=ListRolesResponse, status_code=http_status.HTTP_201_CREATED)
async def create_role(
    role_data: CreateRoleRequest,
    service: TargetRoleService = Depends(get_target_role_service),
):
    dto = TargetRoleCreate(role_key=role_data.role_key, role_label=role_data.role_label)
    try:
        role = await service.create_role(dto)
    except TargetRoleConflictError as err:
        raise TargetRoleConflictValidationError(
            field_name="role_key", value=role_data.role_key, loc="body", detail=err.msg
        )
    return role
