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

from forkflux_api.agents.models import AgentIdentity, TargetRole

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from forkflux_api.agents.dto import AgentApiTokenCreate, AgentIdentityCreate, AgentIdentityRoleAssign, TargetRoleCreate
from forkflux_api.agents.exceptions import (
    AgentApiTokenConflictError,
    AgentIdentityConflictError,
    AgentIdentityNotFoundError,
    AgentIdentityRoleConflictError,
    AgentIdentityRoleNotFoundError,
    TargetRoleConflictError,
    TargetRoleInUseError,
    TargetRoleNotFoundError,
)
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
    TargetRoleService,
)
from forkflux_api.constants import CLIScopeEnum
from forkflux_api.database import session_manager
from forkflux_api.jobs.constants import JobListOrderEnum, JobStatusEnum
from forkflux_api.jobs.dto import HandoffJobFilterParams
from forkflux_api.jobs.exceptions import HandoffJobConflictError, HandoffJobHasChildrenError, HandoffJobNotFoundError
from forkflux_api.jobs.helpers import handoff_job_to_response_model
from forkflux_api.jobs.repositories import HandoffJobRepository, JobArtifactRepository, JobEventRepository
from forkflux_api.jobs.services import HandoffJobService

app = typer.Typer(help="ForkFlux Management CLI")
console = Console()

_CLI_LOGGING_CONFIGURED = False

agents_role_app = typer.Typer(help="Agents role management")
agent_app = typer.Typer(help="Agents management")
job_app = typer.Typer(help="Jobs management")

app.add_typer(agents_role_app, name="agents-role")
app.add_typer(agent_app, name="agent")
app.add_typer(job_app, name="job")


def _format_minutes(value: float | None) -> str:
    if value is None:
        return "-"

    return f"{value:.2f}"


def _format_duration(value: float | None) -> str:
    if value is None:
        return "-"

    rounded_minutes = round(value)
    if rounded_minutes < 60:
        return f"{rounded_minutes}m"

    hours, minutes = divmod(rounded_minutes, 60)
    if minutes == 0:
        return f"{hours}h"

    return f"{hours}h {minutes}m"


def _configure_cli_logging() -> None:
    """Suppress INFO logs for CLI-invoked services, keep WARNING/ERROR visible."""
    global _CLI_LOGGING_CONFIGURED

    if _CLI_LOGGING_CONFIGURED:
        return

    logging.basicConfig(level=logging.WARNING, force=True)
    structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.WARNING))

    _CLI_LOGGING_CONFIGURED = True


async def _apply_fixtures() -> tuple[str, str]:
    _configure_cli_logging()

    console.print("Lets add 2 roles - developer and QA")
    developer_role = await add_role.__wrapped__(role_key="developer", role_label="Developer")
    qa_role = await add_role.__wrapped__(role_key="qa", role_label="QA")

    console.print("Lets add 2 agents - agent-1 and agent-2")
    developer_result = await add_agent.__wrapped__(agent_label="agent-1")
    if developer_result is None:
        console.print("Failed to create API key for agent-1 (developer)", style="bold red")
        raise typer.Exit(code=1)
    developer_agent, developer_token = developer_result

    qa_result = await add_agent.__wrapped__(agent_label="agent-2")
    if qa_result is None:
        console.print("Failed to create API key for agent-2 (qa)", style="bold red")
        raise typer.Exit(code=1)
    qa_agent, qa_token = qa_result

    await assign_agent_role.__wrapped__(agent_id=developer_agent.id, role_key=developer_role.role_key)
    await assign_agent_role.__wrapped__(agent_id=qa_agent.id, role_key=qa_role.role_key)

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


def _download_github_folder(owner: str, repo: str, folder_path: str, save_dir: str, scope: CLIScopeEnum) -> bool:
    if scope == CLIScopeEnum.user:
        local_root = pathlib.Path.home() / save_dir
    else:
        local_root = pathlib.Path(save_dir)
    local_root.mkdir(parents=True, exist_ok=True)

    with httpx.Client() as client:
        try:
            _download_recursive(client, owner, repo, folder_path, local_root)
            return True

        except Exception:
            return False


def _add_mcp_server(cli_name: str, token: str, role_name: str, scope: CLIScopeEnum) -> None:
    cli_display_name = cli_name.capitalize()

    console.print(f"Adding MCP server to the {cli_display_name} CLI with {role_name} token (scope: {scope.value})...")
    subprocess.run(  # noqa: S603
        [
            cli_name,
            "mcp",
            "add",
            "ff",
            "--scope",
            scope.value,
            "--env",
            f"FORKFLUX_API_KEY={token}",
            "--",
            "uvx",
            "forkflux-mcp",
        ],  # noqa: S607
        check=True,
    )
    console.print(f"{cli_display_name} CLI is connected to the ForkFlux bus as a {role_name}", style="green")


def _apply_migrations(db_scope: CLIScopeEnum | None) -> None:
    console.print("Apply database migrations")
    current_dir = os.path.dirname(__file__)
    alembic_cfg = Config(toml_file="../pyproject.toml", attributes={"db_scope": db_scope if db_scope else None})
    alembic_cfg.set_main_option("script_location", os.path.join(current_dir, "migrations"))
    command.upgrade(alembic_cfg, "head")


@app.command(help="Run the server")
def serve(host: str = "0.0.0.0", port: int = 8000) -> None:  # noqa: S104
    _apply_migrations(db_scope=None)

    console.print("Starting server...", style="bold green")
    uvicorn.run(
        "forkflux_api.main:app",
        host=host,
        port=port,
        forwarded_allow_ips="*",
        workers=2,
        loop="none" if sys.platform == "win32" else "auto",
    )


@app.command(help="Initialize the database")
def init() -> None:
    _apply_migrations(db_scope=None)


@app.command(help="Show handoff statistics snapshot")
@lambda f: wraps(f)(lambda *a, **kw: asyncio.run(f(*a, **kw)))
async def stats(
    window_hours: int = typer.Option(24, min=1, help="Metrics window in hours"),
    stuck_minutes: int = typer.Option(60, min=1, help="Stuck-job threshold in minutes"),
    verbose: bool = typer.Option(False, "--verbose", help="Show legacy all-time status counters"),
) -> None:
    _configure_cli_logging()
    trace_id = str(uuid4())

    async with session_manager() as session:
        handoff_job_repo = HandoffJobRepository(session=session, trace_id=trace_id)
        job_artifact_repo = JobArtifactRepository(session=session, trace_id=trace_id)
        job_event_repo = JobEventRepository(session=session, trace_id=trace_id)
        stats_data = await HandoffJobService(
            handoff_job_repo=handoff_job_repo,
            job_artifact_repo=job_artifact_repo,
            job_event_repo=job_event_repo,
            trace_id=trace_id,
        ).stats(window_hours=window_hours, stuck_minutes=stuck_minutes)

    console.print(f"📊 ForkFlux Metrics (Last {stats_data.window_hours}h)")
    console.print()

    pipeline_health_table = Table("[ Pipeline Health ]", "Value")
    pipeline_health_table.add_row("Total jobs", str(stats_data.total_jobs))
    pipeline_health_table.add_row("Completion rate", f"{stats_data.completion_rate * 100:.2f}%")
    pipeline_health_table.add_row("Failure rate", f"{stats_data.failure_rate * 100:.2f}%")
    pipeline_health_table.add_row("Blocked rate", f"{stats_data.blocked_rate * 100:.2f}%")
    pipeline_health_table.add_row("Active agents", str(stats_data.active_agents))
    console.print(pipeline_health_table)

    workflow_impact_table = Table("[ Workflow Impact ]", "Value")
    workflow_impact_table.add_row("Total handoffs", str(stats_data.total_handoffs))
    workflow_impact_table.add_row(
        "Estimated time saved", _format_duration(float(stats_data.estimated_time_saved_minutes))
    )
    console.print(workflow_impact_table)

    latency_table = Table("[ Latency (p50 / p90) ]", "Value")
    latency_table.add_row(
        "Time to claim",
        f"{_format_duration(stats_data.p50_time_to_claim_minutes)} / "
        f"{_format_duration(stats_data.p90_time_to_claim_minutes)}",
    )
    latency_table.add_row(
        "Time to resolution",
        f"{_format_duration(stats_data.p50_time_to_resolution_minutes)} / "
        f"{_format_duration(stats_data.p90_time_to_resolution_minutes)}",
    )
    console.print(latency_table)

    queue_snapshot_table = Table("[ Active Queue Snapshot ]", "Value")

    bottleneck_suffix = ""
    if stats_data.waiting_jobs_by_role:
        role_key, role_count = stats_data.waiting_jobs_by_role[0]
        bottleneck_suffix = f"  (Bottleneck: {role_key} - {role_count} jobs)"

    queue_snapshot_table.add_row(
        "Published (waiting)",
        f"{stats_data.queue_status_counts[JobStatusEnum.PUBLISHED]}{bottleneck_suffix}",
    )
    queue_snapshot_table.add_row("Claimed", str(stats_data.queue_status_counts[JobStatusEnum.CLAIMED]))
    queue_snapshot_table.add_row("In Progress", str(stats_data.queue_status_counts[JobStatusEnum.IN_PROGRESS]))
    queue_snapshot_table.add_row("Blocked", str(stats_data.queue_status_counts[JobStatusEnum.BLOCKED]))
    queue_snapshot_table.add_row(
        f"⚠️ Stuck (>{stats_data.stuck_minutes}m)",
        str(stats_data.stuck_jobs),
    )
    console.print(queue_snapshot_table)

    if verbose:
        console.print()
        legacy_table = Table("[ Historical (All-time Status Counters) ]", "Value")
        for status in JobStatusEnum:
            legacy_table.add_row(f"Status {status.value}", str(stats_data.all_time_status_counts[status]))
        console.print(legacy_table)


@app.command(help="Initialize the database, add some example data, add skills and MCP server")
def quickstart(
    scope: CLIScopeEnum = typer.Option(
        CLIScopeEnum.local, "--scope", "-s", help="Configuration scope for MCP servers and skills"
    ),
) -> None:
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

    _apply_migrations(db_scope=scope)
    developer_token, qa_token = asyncio.run(_apply_fixtures())

    console.print(f"Installing skills (scope: {scope.value})...")
    if "codex" in installed_clis or "opencode" in installed_clis:
        is_agents_skills_downloaded = _download_github_folder("forkflux", "forkflux", "skills", ".agents/skills", scope)
        if not is_agents_skills_downloaded:
            console.print("Failed to install skills for Codex/OpenCode", style="bold red")
    if "claude" in installed_clis:
        is_claude_skills_downloaded = _download_github_folder("forkflux", "forkflux", "skills", ".claude/skills", scope)
        if not is_claude_skills_downloaded:
            console.print("Failed to install skills for Claude", style="bold red")
    if "hermes" in installed_clis:
        # FIXME: `hermes` doesn't support scope yet
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

    _add_mcp_server(installed_clis[0], developer_token, "Developer", scope)
    _add_mcp_server(installed_clis[1], qa_token, "QA", scope)

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
async def add_role(role_key: str, role_label: str) -> TargetRole:
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

    return new_role


@agents_role_app.command("delete")
@lambda f: wraps(f)(lambda *a, **kw: asyncio.run(f(*a, **kw)))
async def delete_role(role_key: str) -> None:
    """
    Deletes a role by key.
    """
    _configure_cli_logging()
    trace_id = str(uuid4())

    delete = typer.confirm(f"Are you sure you want to delete role '{role_key}'?")
    if not delete:
        console.print("Aborting...", style="bold red")
        raise typer.Abort()

    async with session_manager() as session:
        try:
            repo = TargetRoleRepository(session=session, trace_id=trace_id)
            await TargetRoleService(target_role_repo=repo, trace_id=trace_id).delete_role(role_key=role_key)
            console.print(f"Role {role_key} deleted successfully")
        except TargetRoleInUseError:
            console.print(f"Role with key {role_key} is in use and cannot be deleted", style="bold red")
        except TargetRoleNotFoundError:
            console.print(f"Role with key {role_key} not found", style="bold red")


@agent_app.command("list")
@lambda f: wraps(f)(lambda *a, **kw: asyncio.run(f(*a, **kw)))
async def list_agents() -> None:
    _configure_cli_logging()
    trace_id = str(uuid4())

    async with session_manager() as session:
        agent_repo = AgentIdentityRepository(session=session, trace_id=trace_id)
        agent_service = AgentIdentityService(
            agent_identity_repo=agent_repo,
            trace_id=trace_id,
        )
        agents = await agent_service.get_all_agents()
        role_repo = TargetRoleRepository(session=session, trace_id=trace_id)
        roles = await TargetRoleService(target_role_repo=role_repo, trace_id=trace_id).get_all_roles()
        agent_role_repo = AgentIdentityRoleRepository(session=session, trace_id=trace_id)
        agent_role_service = AgentIdentityRoleService(
            agent_identity_role_repo=agent_role_repo,
            trace_id=trace_id,
        )

        roles_mapping = {role.id: role.role_key for role in roles}

        table = Table("ID", "Label", "Role keys")
        for agent in agents:
            role_ids = await agent_role_service.list_role_ids(agent_identity_id=agent.id)
            role_keys = [roles_mapping[role_id] for role_id in role_ids if role_id in roles_mapping]
            table.add_row(str(agent.id), agent.agent_label, ", ".join(role_keys) if role_keys else "-")
        console.print(table)


@agent_app.command("add")
@lambda f: wraps(f)(lambda *a, **kw: asyncio.run(f(*a, **kw)))
async def add_agent(agent_label: str, tool_family: str | None = None) -> tuple[AgentIdentity, str] | None:
    """
    Adds a new agent with the specified label and tool family (optional).
    """
    _configure_cli_logging()
    trace_id = str(uuid4())

    async with session_manager() as session:
        try:
            agent_repo = AgentIdentityRepository(session=session, trace_id=trace_id)
            agent_dto = AgentIdentityCreate(agent_label=agent_label, tool_family=tool_family)
            new_agent = await AgentIdentityService(
                agent_identity_repo=agent_repo,
                trace_id=trace_id,
            ).create_agent(dto=agent_dto)
            console.print(f"Agent {new_agent.agent_label} created successfully")
        except AgentIdentityConflictError:
            console.print("Can't create a new agent", style="bold red")
            return None

        try:
            token_repo = AgentApiTokenRepository(session=session, trace_id=trace_id)
            token_dto = AgentApiTokenCreate(agent_id=new_agent.id)
            new_token = await AgentApiTokenService(agent_api_token_repo=token_repo, trace_id=trace_id).create_token(
                dto=token_dto
            )
            console.print(f"API key {new_token} for agent {new_agent.agent_label} created successfully")
        except AgentApiTokenConflictError:
            console.print("Can't create a new API key", style="bold red")
            return None

    return new_agent, new_token


@agent_app.command("assign-role")
@lambda f: wraps(f)(lambda *a, **kw: asyncio.run(f(*a, **kw)))
async def assign_agent_role(agent_id: int, role_key: str) -> None:
    """
    Assigns a role to an agent.
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

        agent_role_repo = AgentIdentityRoleRepository(session=session, trace_id=trace_id)
        service = AgentIdentityRoleService(
            agent_identity_role_repo=agent_role_repo,
            trace_id=trace_id,
        )

        try:
            await service.assign_role(AgentIdentityRoleAssign(agent_identity_id=agent_id, target_role_id=role.id))
            console.print(f"Role {role_key} assigned to agent {agent_id}")
        except AgentIdentityRoleConflictError:
            console.print(f"Role {role_key} is already assigned to agent {agent_id}", style="bold red")


@agent_app.command("unassign-role")
@lambda f: wraps(f)(lambda *a, **kw: asyncio.run(f(*a, **kw)))
async def unassign_agent_role(agent_id: int, role_key: str) -> None:
    """
    Unassigns a role from an agent.
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

        agent_role_repo = AgentIdentityRoleRepository(session=session, trace_id=trace_id)
        service = AgentIdentityRoleService(
            agent_identity_role_repo=agent_role_repo,
            trace_id=trace_id,
        )

        try:
            await service.unassign_role(agent_identity_id=agent_id, target_role_id=role.id)
            console.print(f"Role {role_key} unassigned from agent {agent_id}")
        except AgentIdentityRoleNotFoundError:
            console.print(f"Role {role_key} is not assigned to agent {agent_id}", style="bold red")


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
        console.print(f"API key for agent {agent_id} revoked successfully")


@job_app.command("list")
@lambda f: wraps(f)(lambda *a, **kw: asyncio.run(f(*a, **kw)))
async def list_jobs(limit: int = 50, status: JobStatusEnum | None = None, target_role_key: str | None = None) -> None:
    _configure_cli_logging()
    trace_id = str(uuid4())

    async with session_manager() as session:
        target_role_ids: list[int] = []
        if target_role_key is not None and target_role_key.strip() != "":
            try:
                role_repo = TargetRoleRepository(session=session, trace_id=trace_id)
                role = await TargetRoleService(target_role_repo=role_repo, trace_id=trace_id).get_by_role_key(
                    target_role_key
                )
                target_role_ids = [role.id]
            except TargetRoleNotFoundError:
                console.print(f"Role with key {target_role_key} not found", style="bold red")
                return

        handoff_job_repo = HandoffJobRepository(session=session, trace_id=trace_id)
        job_artifact_repo = JobArtifactRepository(session=session, trace_id=trace_id)
        job_event_repo = JobEventRepository(session=session, trace_id=trace_id)
        jobs = await HandoffJobService(
            handoff_job_repo=handoff_job_repo,
            job_artifact_repo=job_artifact_repo,
            job_event_repo=job_event_repo,
            trace_id=trace_id,
        ).list_jobs(
            HandoffJobFilterParams(
                limit=limit,
                statuses=[status] if status is not None else [],
                target_role_ids=target_role_ids,
                order=[JobListOrderEnum.CREATED_AT_ASC],
            )
        )

    table = Table("ID", "Summary", "Status", "Priority", "Source", "Assignee", "Target role", "Created at")
    for job in jobs:
        table.add_row(
            str(job.job_details.id),
            job.job_details.summary,
            job.job_details.status.value,
            str(job.job_details.priority),
            job.source_agent_label,
            job.assignee_agent_label or "-",
            job.target_role_key,
            job.job_details.created_at.isoformat(),
        )
    console.print(table)


@job_app.command("details")
@lambda f: wraps(f)(lambda *a, **kw: asyncio.run(f(*a, **kw)))
async def job_details(job_id: int) -> None:
    _configure_cli_logging()
    trace_id = str(uuid4())

    async with session_manager() as session:
        handoff_job_repo = HandoffJobRepository(session=session, trace_id=trace_id)
        job_artifact_repo = JobArtifactRepository(session=session, trace_id=trace_id)
        job_event_repo = JobEventRepository(session=session, trace_id=trace_id)

        try:
            job = await HandoffJobService(
                handoff_job_repo=handoff_job_repo,
                job_artifact_repo=job_artifact_repo,
                job_event_repo=job_event_repo,
                trace_id=trace_id,
            ).get_job_with_artifacts(job_id=job_id)
        except HandoffJobNotFoundError:
            console.print(f"Job with id {job_id} not found", style="bold red")
            return

    response_model = handoff_job_to_response_model(entity=job)
    console.print_json(response_model.model_dump_json(indent=2))


@job_app.command("delete")
@lambda f: wraps(f)(lambda *a, **kw: asyncio.run(f(*a, **kw)))
async def delete_job(job_id: int) -> None:
    _configure_cli_logging()
    trace_id = str(uuid4())

    delete = typer.confirm(f"Are you sure you want to delete job '{job_id}'?")
    if not delete:
        console.print("Aborting...", style="bold red")
        raise typer.Abort()

    async with session_manager() as session:
        handoff_job_repo = HandoffJobRepository(session=session, trace_id=trace_id)
        job_artifact_repo = JobArtifactRepository(session=session, trace_id=trace_id)
        job_event_repo = JobEventRepository(session=session, trace_id=trace_id)

        try:
            await HandoffJobService(
                handoff_job_repo=handoff_job_repo,
                job_artifact_repo=job_artifact_repo,
                job_event_repo=job_event_repo,
                trace_id=trace_id,
            ).delete_job(job_id=job_id)
        except HandoffJobNotFoundError:
            console.print(f"Job with id {job_id} not found", style="bold red")
            return
        except HandoffJobHasChildrenError:
            console.print(f"Job with id {job_id} has child jobs and cannot be deleted", style="bold red")
            return
        except HandoffJobConflictError:
            console.print(f"Cannot delete job {job_id}", style="bold red")
            return

    console.print(f"Job {job_id} deleted successfully")


@job_app.command("change-status")
@lambda f: wraps(f)(lambda *a, **kw: asyncio.run(f(*a, **kw)))
async def change_job_status(
    job_id: int,
    status: JobStatusEnum,
    agent_id: int,
    failure_reason: str | None = None,
    blocked_reason: str | None = None,
    unblock_reason: str | None = None,
) -> None:
    _configure_cli_logging()
    trace_id = str(uuid4())

    async with session_manager() as session:
        try:
            agent_repo = AgentIdentityRepository(session=session, trace_id=trace_id)
            agent = await AgentIdentityService(
                agent_identity_repo=agent_repo,
                trace_id=trace_id,
            ).get_by_id(agent_identity_id=agent_id)
        except AgentIdentityNotFoundError:
            console.print(f"Agent with id {agent_id} not found", style="bold red")
            return

        handoff_job_repo = HandoffJobRepository(session=session, trace_id=trace_id)
        job_artifact_repo = JobArtifactRepository(session=session, trace_id=trace_id)
        job_event_repo = JobEventRepository(session=session, trace_id=trace_id)

        try:
            await HandoffJobService(
                handoff_job_repo=handoff_job_repo,
                job_artifact_repo=job_artifact_repo,
                job_event_repo=job_event_repo,
                trace_id=trace_id,
            ).change_job_status(
                job_id=job_id,
                status=status,
                agent_id=agent.id,
                failure_reason=failure_reason,
                blocked_reason=blocked_reason,
                unblock_reason=unblock_reason,
            )
        except HandoffJobNotFoundError:
            console.print(f"Job with id {job_id} not found", style="bold red")
            return
        except HandoffJobConflictError:
            console.print(f"Cannot change status for job {job_id}", style="bold red")
            return

    console.print(f"Job {job_id} status changed to {status.value} successfully")


if __name__ == "__main__":
    app()
