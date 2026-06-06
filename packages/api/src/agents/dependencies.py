from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from src.agents.respositories import TargetRoleRepository
from src.agents.services import TargetRoleService
from src.database import get_session


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
