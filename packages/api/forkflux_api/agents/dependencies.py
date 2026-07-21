from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from forkflux_api.agents.repositories import (
    AgentApiTokenRepository,
    AgentIdentityRepository,
    AgentIdentityRoleRepository,
    TargetRoleRepository,
)
from forkflux_api.agents.services import (
    AgentApiTokenService,
    AgentIdentityRoleService,
    AgentIdentityService,
    AgentRegistrationUseCase,
    TargetRoleService,
)
from forkflux_api.database import get_session


def get_trace_id(request: Request) -> str:
    return request.state.trace_id


def get_target_role_repo(
    session: AsyncSession = Depends(get_session), trace_id: str = Depends(get_trace_id)
) -> TargetRoleRepository:
    return TargetRoleRepository(session=session, trace_id=trace_id)


def get_target_role_service(
    repository: TargetRoleRepository = Depends(get_target_role_repo), trace_id: str = Depends(get_trace_id)
) -> TargetRoleService:
    return TargetRoleService(target_role_repo=repository, trace_id=trace_id)


def get_agent_identity_repo(
    session: AsyncSession = Depends(get_session), trace_id: str = Depends(get_trace_id)
) -> AgentIdentityRepository:
    return AgentIdentityRepository(session=session, trace_id=trace_id)


def get_agent_identity_role_repo(
    session: AsyncSession = Depends(get_session), trace_id: str = Depends(get_trace_id)
) -> AgentIdentityRoleRepository:
    return AgentIdentityRoleRepository(session=session, trace_id=trace_id)


def get_agent_api_token_repo(
    session: AsyncSession = Depends(get_session), trace_id: str = Depends(get_trace_id)
) -> AgentApiTokenRepository:
    return AgentApiTokenRepository(session=session, trace_id=trace_id)


def get_agent_identity_service(
    repository: AgentIdentityRepository = Depends(get_agent_identity_repo),
    trace_id: str = Depends(get_trace_id),
) -> AgentIdentityService:
    return AgentIdentityService(agent_identity_repo=repository, trace_id=trace_id)


def get_agent_identity_roles_service(
    repository: AgentIdentityRoleRepository = Depends(get_agent_identity_role_repo),
    trace_id: str = Depends(get_trace_id),
) -> AgentIdentityRoleService:
    return AgentIdentityRoleService(agent_identity_role_repo=repository, trace_id=trace_id)


def get_agent_api_token_service(
    repository: AgentApiTokenRepository = Depends(get_agent_api_token_repo),
    trace_id: str = Depends(get_trace_id),
) -> AgentApiTokenService:
    return AgentApiTokenService(agent_api_token_repo=repository, trace_id=trace_id)


def get_agent_registration_use_case(
    target_role_service: TargetRoleService = Depends(get_target_role_service),
    agent_identity_service: AgentIdentityService = Depends(get_agent_identity_service),
    agent_identity_role_service: AgentIdentityRoleService = Depends(get_agent_identity_roles_service),
    agent_api_token_service: AgentApiTokenService = Depends(get_agent_api_token_service),
    trace_id: str = Depends(get_trace_id),
) -> AgentRegistrationUseCase:
    return AgentRegistrationUseCase(
        target_role_service=target_role_service,
        agent_identity_service=agent_identity_service,
        agent_identity_role_service=agent_identity_role_service,
        agent_api_token_service=agent_api_token_service,
        trace_id=trace_id,
    )
