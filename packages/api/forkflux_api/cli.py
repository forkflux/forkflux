import asyncio
import logging
import os
import pathlib
import subprocess
import sys
from functools import wraps
from uuid import uuid4

import httpx
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


async def _init_async() -> tuple[str, str]:
    _configure_cli_logging()

    console.print("Lets add 2 roles - developer and QA")
    await add_role.__wrapped__(role_key="developer", role_label="Developer")
    await add_role.__wrapped__(role_key="qa", role_label="QA")

    console.print("Lets add 2 agents - agent-1 and agent-2")
    developer_token = await add_agent.__wrapped__(agent_label="agent-1", role_key="developer")
    qa_token = await add_agent.__wrapped__(agent_label="agent-2", role_key="qa")

    if developer_token is None:
        console.print("Failed to create token for agent-1 (developer)", style="bold red")
        raise typer.Exit(code=1)

    if qa_token is None:
        console.print("Failed to create token for agent-2 (qa)", style="bold red")
        raise typer.Exit(code=1)

    return developer_token, qa_token


def _check_cli_version(command_name: str) -> bool:
    try:
        subprocess.run([command_name, "--version"], capture_output=True, text=True, check=True)  # noqa: S603
        return True
    except FileNotFoundError, subprocess.CalledProcessError:
        return False


def _download_recursive(
    client: httpx.Client, owner: str, repo: str, github_path: str, local_path: pathlib.Path
) -> None:
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{github_path}"

    response = client.get(api_url)
    response.raise_for_status()
    items = response.json()

    for item in items:
        if item["type"] == "file":
            file_response = client.get(item["download_url"])
            file_response.raise_for_status()

            target_file_path = local_path / item["name"]
            target_file_path.write_bytes(file_response.content)

        elif item["type"] == "dir":
            new_local_path = local_path / item["name"]
            new_local_path.mkdir(parents=True, exist_ok=True)

            _download_recursive(client, owner, repo, item["path"], new_local_path)


def _download_github_folder(owner: str, repo: str, folder_path: str, save_dir: str) -> bool:
    local_root = pathlib.Path(save_dir)
    local_root.mkdir(parents=True, exist_ok=True)

    with httpx.Client() as client:
        try:
            _download_recursive(client, owner, repo, folder_path, local_root)
            return True

        except Exception:
            return False


def _add_mcp_server(cli_name: str, token: str, role_name: str) -> None:
    cli_display_name = cli_name.capitalize()

    console.print(f"Adding MCP server to the {cli_display_name} CLI with {role_name} token...")
    subprocess.run(  # noqa: S603
        [cli_name, "mcp", "add", "ff", "--env", f"FORKFLUX_API_KEY={token}", "--", "uvx", "forkflux-mcp"],  # noqa: S607
        check=True,
    )
    console.print(f"{cli_display_name} CLI is connected to the ForkFlux bus as a {role_name}", style="green")


def _apply_migrations() -> None:
    console.print("Apply database migrations")
    current_dir = os.path.dirname(__file__)
    alembic_cfg = Config(toml_file="../pyproject.toml")
    alembic_cfg.set_main_option("script_location", os.path.join(current_dir, "migrations"))
    command.upgrade(alembic_cfg, "head")


@app.command(help="Run the server")
def serve(host: str = "0.0.0.0", port: int = 8000) -> None:  # noqa: S104
    _apply_migrations()

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
    _apply_migrations()

    asyncio.run(_init_async())


@app.command(help="Initialize the database, add some example data, add skills and MCP server")
def quickstart() -> None:
    is_codex_installed = _check_cli_version("codex")
    is_claude_installed = _check_cli_version("claude")
    is_opencode_installed = _check_cli_version("opencode")
    is_hermes_installed = _check_cli_version("hermes")

    installed_clis = []
    if is_codex_installed:
        installed_clis.append("codex")
    if is_claude_installed:
        installed_clis.append("claude")
    if is_opencode_installed:
        installed_clis.append("opencode")
    if is_hermes_installed:
        installed_clis.append("hermes")

    if len(installed_clis) < 2:
        console.print(
            "Codex, Claude Code, OpenCode, or Hermes are not installed, please install two of them first",
            style="bold red",
        )
        return

    _apply_migrations()
    developer_token, qa_token = asyncio.run(_init_async())

    console.print("Installing skills...")
    if "codex" in installed_clis or "opencode" in installed_clis:
        is_agents_skills_downloaded = _download_github_folder("forkflux", "forkflux", "skills", ".agents/skills")
        if not is_agents_skills_downloaded:
            console.print("Failed to install skills for Codex/OpenCode", style="bold red")
    if "claude" in installed_clis:
        is_claude_skills_downloaded = _download_github_folder("forkflux", "forkflux", "skills", ".claude/skills")
        if not is_claude_skills_downloaded:
            console.print("Failed to install skills for Claude", style="bold red")
    if "hermes" in installed_clis:
        subprocess.run(  # noqa: S603
            ["hermes", "skills", "tap", "add", "forkflux/forkflux"],  # noqa: S607
            check=True,
        )
        subprocess.run(  # noqa: S603
            ["hermes", "skills", "install", "forkflux/forkflux/forkflux-receiver", "--force"],  # noqa: S607
            check=True,
        )
        subprocess.run(  # noqa: S603
            ["hermes", "skills", "install", "forkflux/forkflux/forkflux-sender", "--force"],  # noqa: S607
            check=True,
        )

    _add_mcp_server(installed_clis[0], developer_token, "Developer")
    _add_mcp_server(installed_clis[1], qa_token, "QA")

    console.print("Everything for handoff is ready.")
    console.print("Only one step left! Run the server with:")
    console.print("uvx --from forkflux-api forkflux serve", style="bold green")


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
async def add_agent(agent_label: str, role_key: str, tool_family: str | None = None) -> str | None:
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
            return None

        try:
            agent_repo = AgentIdentityRepository(session=session, trace_id=trace_id)
            agent_dto = AgentIdentityCreate(agent_label=agent_label, role_id=role.id, tool_family=tool_family)
            new_agent = await AgentIdentityService(agent_identity_repo=agent_repo, trace_id=trace_id).create_agent(
                dto=agent_dto
            )
            console.print(f"Agent {new_agent.agent_label} created successfully")
        except AgentIdentityConflictError:
            console.print("Can't create new agent", style="bold red")
            return None

        try:
            token_repo = AgentApiTokenRepository(session=session, trace_id=trace_id)
            token_dto = AgentApiTokenCreate(agent_id=new_agent.id)
            new_token = await AgentApiTokenService(agent_api_token_repo=token_repo, trace_id=trace_id).create_token(
                dto=token_dto
            )
            console.print(f"Token {new_token} for agent {new_agent.agent_label} created successfully")
            return new_token
        except AgentApiTokenConflictError:
            console.print("Can't create new token", style="bold red")
            return None


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
