import hashlib
import hmac

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from forkflux_api.agents.exceptions import AgentApiTokenNotFoundError, AgentIdentityNotFoundError
from forkflux_api.agents.models import AgentIdentity
from forkflux_api.agents.respositories import AgentApiTokenRepository, AgentIdentityRepository
from forkflux_api.agents.services import AgentApiTokenService, AgentIdentityService
from forkflux_api.database import get_session

bearer_scheme = HTTPBearer(auto_error=False)


def get_trace_id(request: Request) -> str:
    return request.state.trace_id


def get_agent_api_token_repo(
    session: AsyncSession = Depends(get_session), trace_id: str = Depends(get_trace_id)
) -> AgentApiTokenRepository:
    return AgentApiTokenRepository(session=session, trace_id=trace_id)


def get_agent_api_token_service(
    repository: AgentApiTokenRepository = Depends(get_agent_api_token_repo), trace_id: str = Depends(get_trace_id)
) -> AgentApiTokenService:
    return AgentApiTokenService(agent_api_token_repo=repository, trace_id=trace_id)


def get_agent_identity_repo(
    session: AsyncSession = Depends(get_session), trace_id: str = Depends(get_trace_id)
) -> AgentIdentityRepository:
    return AgentIdentityRepository(session=session, trace_id=trace_id)


def get_agent_identity_service(
    repository: AgentIdentityRepository = Depends(get_agent_identity_repo), trace_id: str = Depends(get_trace_id)
) -> AgentIdentityService:
    return AgentIdentityService(agent_identity_repo=repository, trace_id=trace_id)


async def verify_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    service: AgentApiTokenService = Depends(get_agent_api_token_service),
) -> dict[str, int]:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authenticated",
        )

    token = credentials.credentials
    provided_hash = hashlib.sha256(token.encode()).hexdigest()

    try:
        entity = await service.get_token(token_hash=provided_hash)

        if not hmac.compare_digest(provided_hash, entity.token_hash):
            raise AgentApiTokenNotFoundError

        return {"agent_id": entity.agent_id}
    except AgentApiTokenNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_agent(
    payload: dict[str, int] = Depends(verify_token),
    agent_service: AgentIdentityService = Depends(get_agent_identity_service),
) -> AgentIdentity:
    agent_id = payload["agent_id"]

    try:
        agent = await agent_service.get_by_id(agent_id)
    except AgentIdentityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Agent not found",
        )

    return agent
