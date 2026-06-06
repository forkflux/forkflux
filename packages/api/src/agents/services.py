import structlog

from src.agents.models import AgentApiToken, AgentIdentity, TargetRole
from src.agents.respositories import AgentApiTokenRepository, AgentIdentityRepository, TargetRoleRepository


class TargetRoleService:
    def __init__(self, target_role_repo: TargetRoleRepository, trace_id: str) -> None:
        self._logger = structlog.get_logger().bind(cls=self.__class__.__name__, trace_id=trace_id)
        self._target_role_repo = target_role_repo

    async def get_all_roles(self) -> list[TargetRole]:
        return await self._target_role_repo.list()


class AgentApiTokenService:
    def __init__(self, agent_api_token_repo: AgentApiTokenRepository, trace_id: str) -> None:
        self._logger = structlog.get_logger().bind(cls=self.__class__.__name__, trace_id=trace_id)
        self._agent_api_token_repo = agent_api_token_repo

    async def get_token(self, token_hash: str) -> AgentApiToken:
        return await self._agent_api_token_repo.get(token_hash)


class AgentIdentityService:
    def __init__(self, agent_identity_repo: AgentIdentityRepository, trace_id: str) -> None:
        self._logger = structlog.get_logger().bind(cls=self.__class__.__name__, trace_id=trace_id)
        self._agent_identity_repo = agent_identity_repo

    async def get_by_id(self, agent_identity_id: int) -> AgentIdentity:
        return await self._agent_identity_repo.get_by_id(agent_identity_id)
