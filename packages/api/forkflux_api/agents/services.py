import hashlib
import secrets

import structlog

from forkflux_api.agents.dto import (
    AgentApiTokenCreate,
    AgentIdentityCreate,
    AgentIdentityRoleAssign,
    AgentIdentityWithRoles,
    AgentRegistration,
    AgentRegistrationResult,
    RoleSummary,
    TargetRoleCreate,
)
from forkflux_api.agents.exceptions import TargetRoleNotFoundError
from forkflux_api.agents.models import AgentApiToken, AgentIdentity, AgentIdentityRole, TargetRole
from forkflux_api.agents.repositories import (
    AgentApiTokenRepository,
    AgentIdentityRepository,
    AgentIdentityRoleRepository,
    TargetRoleRepository,
)


class TargetRoleService:
    def __init__(self, target_role_repo: TargetRoleRepository, trace_id: str) -> None:
        self._logger = structlog.get_logger().bind(cls=self.__class__.__name__, trace_id=trace_id)
        self._target_role_repo = target_role_repo

    async def get_all_roles(self) -> list[TargetRole]:
        log = self._logger.bind(method="get_all_roles")
        log.info("operation_started")

        roles = await self._target_role_repo.list()

        log.info("operation_completed", roles_count=len(roles))
        return roles

    async def get_roles_by_ids(self, ids: list[int]) -> list[TargetRole]:
        log = self._logger.bind(method="get_roles_by_ids", ids=ids)
        log.info("operation_started")

        roles = await self._target_role_repo.list_by_ids(ids)

        log.info("operation_completed", roles_count=len(roles))
        return roles

    async def get_by_role_key(self, role_key: str) -> TargetRole:
        log = self._logger.bind(method="get_by_role_key", role_key=role_key)
        log.info("operation_started")

        role = await self._target_role_repo.get_by_role_key(role_key)

        log.info("operation_completed")
        return role

    async def is_role_exists(self, role_key: str) -> bool:
        log = self._logger.bind(method="is_role_exists", role_key=role_key)
        log.info("operation_started")

        exists = await self._target_role_repo.exists(role_key)

        log.info("operation_completed", role_exists=exists)
        return exists

    async def create_role(self, dto: TargetRoleCreate) -> TargetRole:
        log = self._logger.bind(method="create_role", role_key=dto.role_key)
        log.info("operation_started")

        role = await self._target_role_repo.create(dto)

        log.info("operation_completed")
        return role

    async def delete_role(self, role_key: str) -> None:
        log = self._logger.bind(method="delete_role", role_key=role_key)
        log.info("operation_started")

        await self._target_role_repo.delete(role_key)

        log.info("operation_completed")
        return None


class AgentApiTokenService:
    def __init__(self, agent_api_token_repo: AgentApiTokenRepository, trace_id: str) -> None:
        self._logger = structlog.get_logger().bind(cls=self.__class__.__name__, trace_id=trace_id)
        self._agent_api_token_repo = agent_api_token_repo

    async def get_token(self, token_hash: str) -> AgentApiToken:
        log = self._logger.bind(method="get_token", token_hash=token_hash)
        log.info("operation_started")

        token = await self._agent_api_token_repo.get(token_hash)

        log.info("operation_completed", token_id=token.id, agent_id=token.agent_id)
        return token

    async def create_token(self, dto: AgentApiTokenCreate) -> str:
        log = self._logger.bind(method="create_token", agent_id=dto.agent_id)
        log.info("operation_started")

        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        await self._agent_api_token_repo.create(dto=dto, token_hash=token_hash)

        log.info("operation_completed")
        return raw_token

    async def revoke_token(self, agent_id: int) -> int:
        log = self._logger.bind(method="revoke_token", agent_id=agent_id)
        log.info("operation_started")

        revoked_count = await self._agent_api_token_repo.revoke(agent_id)

        log.info("operation_completed", revoked_count=revoked_count)
        return revoked_count


class AgentIdentityService:
    def __init__(self, agent_identity_repo: AgentIdentityRepository, trace_id: str) -> None:
        self._logger = structlog.get_logger().bind(cls=self.__class__.__name__, trace_id=trace_id)
        self._agent_identity_repo = agent_identity_repo

    async def get_all_agents(self) -> list[AgentIdentity]:
        log = self._logger.bind(method="get_all_agents")
        log.info("operation_started")

        agents = await self._agent_identity_repo.list()

        log.info("operation_completed", agents_count=len(agents))
        return agents

    async def list_with_roles(self) -> list[AgentIdentityWithRoles]:
        log = self._logger.bind(method="list_with_roles")
        log.info("operation_started")

        agents = await self._agent_identity_repo.list_with_roles()

        result = [
            AgentIdentityWithRoles(
                id=agent.id,
                agent_label=agent.agent_label,
                tool_family=agent.tool_family,
                created_at=agent.created_at,
                roles=[
                    RoleSummary(
                        role_key=assignment.target_role.role_key,
                        role_label=assignment.target_role.role_label,
                    )
                    for assignment in agent.role_assignments
                ],
            )
            for agent in agents
        ]

        log.info("operation_completed", agents_count=len(result))
        return result

    async def get_by_id(self, agent_identity_id: int) -> AgentIdentity:
        log = self._logger.bind(method="get_by_id", agent_identity_id=agent_identity_id)
        log.info("operation_started")

        agent = await self._agent_identity_repo.get_by_id(agent_identity_id)

        log.info("operation_completed")
        return agent

    async def create_agent(self, dto: AgentIdentityCreate) -> AgentIdentity:
        log = self._logger.bind(method="create_agent", agent_label=dto.agent_label)
        log.info("operation_started")

        agent = await self._agent_identity_repo.create(dto)

        log.info("operation_completed", agent_identity_id=agent.id)
        return agent


class AgentIdentityRoleService:
    def __init__(self, agent_identity_role_repo: AgentIdentityRoleRepository, trace_id: str) -> None:
        self._logger = structlog.get_logger().bind(cls=self.__class__.__name__, trace_id=trace_id)
        self._agent_identity_role_repo = agent_identity_role_repo

    async def assign_role(self, dto: AgentIdentityRoleAssign) -> AgentIdentityRole:
        log = self._logger.bind(
            method="assign_role",
            agent_identity_id=dto.agent_identity_id,
            target_role_id=dto.target_role_id,
        )
        log.info("operation_started")

        assignment = await self._agent_identity_role_repo.assign(dto)

        log.info("operation_completed", assignment_id=assignment.id)
        return assignment

    async def unassign_role(self, agent_identity_id: int, target_role_id: int) -> None:
        log = self._logger.bind(
            method="unassign_role",
            agent_identity_id=agent_identity_id,
            target_role_id=target_role_id,
        )
        log.info("operation_started")

        await self._agent_identity_role_repo.remove(
            agent_identity_id=agent_identity_id,
            target_role_id=target_role_id,
        )

        log.info("operation_completed")

    async def list_role_ids(self, agent_identity_id: int) -> list[int]:
        log = self._logger.bind(method="list_role_ids", agent_identity_id=agent_identity_id)
        log.info("operation_started")

        role_ids = await self._agent_identity_role_repo.list_role_ids_for_agent(agent_identity_id=agent_identity_id)

        log.info("operation_completed", roles_count=len(role_ids))
        return role_ids


class AgentRegistrationUseCase:
    def __init__(
        self,
        target_role_service: TargetRoleService,
        agent_identity_service: AgentIdentityService,
        agent_identity_role_service: AgentIdentityRoleService,
        agent_api_token_service: AgentApiTokenService,
        trace_id: str,
    ) -> None:
        self._logger = structlog.get_logger().bind(cls=self.__class__.__name__, trace_id=trace_id)
        self._target_role_service = target_role_service
        self._agent_identity_service = agent_identity_service
        self._agent_identity_role_service = agent_identity_role_service
        self._agent_api_token_service = agent_api_token_service

    async def register_agent(self, dto: AgentRegistration) -> AgentRegistrationResult:
        log = self._logger.bind(
            method="register_agent", agent_label=dto.agent_label, target_role_ids=dto.target_role_ids
        )
        log.info("operation_started")

        roles = await self._target_role_service.get_roles_by_ids(dto.target_role_ids)
        if len(roles) != len(dto.target_role_ids):
            log.info("target_roles_not_found", requested=len(dto.target_role_ids), found=len(roles))
            raise TargetRoleNotFoundError

        agent = await self._agent_identity_service.create_agent(
            AgentIdentityCreate(agent_label=dto.agent_label, tool_family=dto.tool_family)
        )

        for target_role_id in dto.target_role_ids:
            await self._agent_identity_role_service.assign_role(
                AgentIdentityRoleAssign(agent_identity_id=agent.id, target_role_id=target_role_id)
            )

        api_token = await self._agent_api_token_service.create_token(AgentApiTokenCreate(agent_id=agent.id))

        log.info("operation_completed", agent_identity_id=agent.id)
        return AgentRegistrationResult(
            agent_id=agent.id,
            agent_label=dto.agent_label,
            tool_family=dto.tool_family,
            target_role_ids=list(dto.target_role_ids),
            api_token=api_token,
        )
