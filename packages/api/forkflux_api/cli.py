import asyncio
import logging
import os
import pathlib
import sys
from functools import wraps
from uuid import uuid4

import structlog
import typer
import uvicorn
from alembic import command
from alembic.config import Config
from rich.console import Console
from rich.table import Table

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from forkflux_api.agents.dto import AgentApiTokenCreate, AgentIdentityCreate, TargetRoleCreate
from forkflux_api.agents.exceptions import (
    AgentApiTokenConflictError,
    AgentIdentityConflictError,
    TargetRoleConflictError,
    TargetRoleNotFoundError,
)
from forkflux_api.agents.respositories import AgentApiTokenRepository, AgentIdentityRepository, TargetRoleRepository
from forkflux_api.agents.services import AgentApiTokenService, AgentIdentityService, TargetRoleService
from forkflux_api.database import session_manager

app = typer.Typer(help="ForkFlux Management CLI")
console = Console()

_CLI_LOGGING_CONFIGURED = False

agents_role_app = typer.Typer(help="Agents role management")
agent_app = typer.Typer(help="Agents management")

app.add_typer(agents_role_app, name="agents-role")
app.add_typer(agent_app, name="agent")


def _configure_cli_logging() -> None:
    """Suppress INFO logs for CLI-invoked services, keep WARNING/ERROR visible."""
    global _CLI_LOGGING_CONFIGURED

    if _CLI_LOGGING_CONFIGURED:
        return

    logging.basicConfig(level=logging.WARNING, force=True)
    structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.WARNING))

    _CLI_LOGGING_CONFIGURED = True


def apply_migrations() -> None:
    console.print("Apply database migrations")
    current_dir = os.path.dirname(__file__)
    alembic_cfg = Config(toml_file="../pyproject.toml")
    alembic_cfg.set_main_option("script_location", os.path.join(current_dir, "migrations"))
    command.upgrade(alembic_cfg, "head")


@app.command(help="Run the server")
def serve(host: str = "0.0.0.0", port: int = 8080) -> None:  # noqa: S104
    apply_migrations()

    console.print("Starting server...", style="bold green")
    uvicorn.run(
        "forkflux_api.main:app",
        host=host,
        port=port,
        forwarded_allow_ips="*",
        workers=2,
        loop="none" if sys.platform == "win32" else "auto",
    )


@app.command(help="Initialize the database and add some example data")
def init() -> None:
    apply_migrations()

    asyncio.run(_init_async())


async def _init_async() -> None:
    _configure_cli_logging()

    console.print("Lets add 2 roles - developer and QA")
    await add_role.__wrapped__(role_key="developer", role_label="Developer")
    await add_role.__wrapped__(role_key="qa", role_label="QA")

    console.print("Lets add 2 agents - agent-1 and agent-2")
    await add_agent.__wrapped__(agent_label="agent-1", role_key="developer")
    await add_agent.__wrapped__(agent_label="agent-2", role_key="qa")


@agents_role_app.command("list")
@lambda f: wraps(f)(lambda *a, **kw: asyncio.run(f(*a, **kw)))
async def list_roles() -> None:
    _configure_cli_logging()
    trace_id = str(uuid4())

    async with session_manager() as session:
        repo = TargetRoleRepository(session=session, trace_id=trace_id)
        roles = await TargetRoleService(target_role_repo=repo, trace_id=trace_id).get_all_roles()

    table = Table("Key", "Label")
    for role in roles:
        table.add_row(role.role_key, role.role_label)
    console.print(table)


@agents_role_app.command("add")
@lambda f: wraps(f)(lambda *a, **kw: asyncio.run(f(*a, **kw)))
async def add_role(role_key: str, role_label: str) -> None:
    """
    Adds a new role with the specified key and label.
    """
    _configure_cli_logging()
    trace_id = str(uuid4())

    async with session_manager() as session:
        try:
            repo = TargetRoleRepository(session=session, trace_id=trace_id)
            dto = TargetRoleCreate(role_key=role_key, role_label=role_label)
            new_role = await TargetRoleService(target_role_repo=repo, trace_id=trace_id).create_role(dto=dto)
            console.print(f"Role {new_role.role_key} created successfully")
        except TargetRoleConflictError:
            console.print(f"Role with key {role_key} already exists", style="bold red")


@agent_app.command("list")
@lambda f: wraps(f)(lambda *a, **kw: asyncio.run(f(*a, **kw)))
async def list_agents() -> None:
    _configure_cli_logging()
    trace_id = str(uuid4())

    async with session_manager() as session:
        agent_repo = AgentIdentityRepository(session=session, trace_id=trace_id)
        agents = await AgentIdentityService(agent_identity_repo=agent_repo, trace_id=trace_id).get_all_agents()
        role_repo = TargetRoleRepository(session=session, trace_id=trace_id)
        roles = await TargetRoleService(target_role_repo=role_repo, trace_id=trace_id).get_all_roles()

    roles_mapping = {role.id: role.role_key for role in roles}

    table = Table("ID", "Label", "Role key")
    for agent in agents:
        table.add_row(str(agent.id), agent.agent_label, roles_mapping[agent.role_id])
    console.print(table)


@agent_app.command("add")
@lambda f: wraps(f)(lambda *a, **kw: asyncio.run(f(*a, **kw)))
async def add_agent(agent_label: str, role_key: str, tool_family: str | None = None) -> None:
    """
    Adds a new agent with the specified label, role, and tool family (optional).
    """
    _configure_cli_logging()
    trace_id = str(uuid4())

    async with session_manager() as session:
        try:
            role_repo = TargetRoleRepository(session=session, trace_id=trace_id)
            role = await TargetRoleService(target_role_repo=role_repo, trace_id=trace_id).get_by_role_key(role_key)
        except TargetRoleNotFoundError:
            console.print(f"Role with key {role_key} not found", style="bold red")
            return

        try:
            agent_repo = AgentIdentityRepository(session=session, trace_id=trace_id)
            agent_dto = AgentIdentityCreate(agent_label=agent_label, role_id=role.id, tool_family=tool_family)
            new_agent = await AgentIdentityService(agent_identity_repo=agent_repo, trace_id=trace_id).create_agent(
                dto=agent_dto
            )
            console.print(f"Agent {new_agent.agent_label} created successfully")
        except AgentIdentityConflictError:
            console.print("Can't create new agent", style="bold red")
            return

        try:
            token_repo = AgentApiTokenRepository(session=session, trace_id=trace_id)
            token_dto = AgentApiTokenCreate(agent_id=new_agent.id)
            new_token = await AgentApiTokenService(agent_api_token_repo=token_repo, trace_id=trace_id).create_token(
                dto=token_dto
            )
            console.print(f"Token {new_token} for agent {new_agent.agent_label} created successfully")
        except AgentApiTokenConflictError:
            console.print("Can't create new token", style="bold red")
            return


@agent_app.command("revoke-token")
@lambda f: wraps(f)(lambda *a, **kw: asyncio.run(f(*a, **kw)))
async def agent_revoke_token(agent_id: int) -> None:
    """
    Revokes the token associated with a specified agent.
    """
    _configure_cli_logging()
    trace_id = str(uuid4())

    async with session_manager() as session:
        token_repo = AgentApiTokenRepository(session=session, trace_id=trace_id)
        await AgentApiTokenService(agent_api_token_repo=token_repo, trace_id=trace_id).revoke_token(agent_id=agent_id)
        console.print(f"Token for agent {agent_id} revoked successfully")


if __name__ == "__main__":
    app()
