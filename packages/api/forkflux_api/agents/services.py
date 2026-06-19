import hashlib
import secrets

import structlog
from forkflux_api.agents.dto import AgentApiTokenCreate, AgentIdentityCreate, TargetRoleCreate
from forkflux_api.agents.models import AgentApiToken, AgentIdentity, TargetRole
from forkflux_api.agents.respositories import AgentApiTokenRepository, AgentIdentityRepository, TargetRoleRepository


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

    async def get_by_id(self, agent_identity_id: int) -> AgentIdentity:
        log = self._logger.bind(method="get_by_id", agent_identity_id=agent_identity_id)
        log.info("operation_started")

        agent = await self._agent_identity_repo.get_by_id(agent_identity_id)

        log.info("operation_completed")
        return agent

    async def create_agent(self, dto: AgentIdentityCreate) -> AgentIdentity:
        log = self._logger.bind(method="create_agent", agent_label=dto.agent_label, role_id=dto.role_id)
        log.info("operation_started")

        agent = await self._agent_identity_repo.create(dto)

        log.info("operation_completed", agent_identity_id=agent.id)
        return agent
