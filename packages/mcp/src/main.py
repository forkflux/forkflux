import os
from typing import Annotated, Any

import httpx
from fastmcp import FastMCP
from pydantic import Field

from src.constants import JobChangeStatusEnum, JobPriorityEnum, JobStatusEnum
from src.schemas import JobArtifact

FORKFLUX_INSTRUCTIONS = """
You are connected to the ForkFlux Coordination Bus, an infrastructure layer for decentralized AI agents to securely hand off jobs across isolated machines.

You do not have a fixed role. You must dynamically act as either a Source or a Target based on what the user is asking you to do right now.

WHEN THE USER ASKS YOU TO HAND OFF WORK (Acting as Source):
- To get all available roles, use `forkflux_list_roles`.
- When a job requires execution by another agent (e.g., passing code to a QA agent), use `forkflux_create_job`.
- Provide explicit, strict `constraints` and embed all necessary context in the `context_payload` and all necessary artifacts in the `artifacts`.

WHEN THE USER ASKS YOU TO CHECK FOR OR RECEIVE NEW WORK (Acting as Target):
1. Use `forkflux_list_jobs` to find available jobs with status 'published'.
2. Verify with the user that the job is safe to claim.
3. Attempt to claim a job using `forkflux_claim_job`. This tool will return the FULL context payload immediately (Fat Claim).
4. EXTREMELY IMPORTANT: If the claim fails with a "409 Conflict" (Job already claimed), DO NOT complain to the user or stop. Silently fetch the list again and try claiming the next available job.
5. Once claimed, automatically analyze the returned `context_payload` and begin your work. Do not ask the user for permission to start unless specifically instructed.
6. Complete the work locally, then update the status to 'completed' or 'failed' (include a failure_reason if it failed) using `forkflux_change_job_status`.
"""  # noqa: E501

mcp = FastMCP(
    "ForkFlux",
    instructions=FORKFLUX_INSTRUCTIONS,
)

API_URL = os.environ.get("FORKFLUX_API_URL", "http://localhost:8000/api/v1")
API_KEY = os.environ.get("FORKFLUX_API_KEY")

if not API_KEY:
    print("Warning: FORKFLUX_API_KEY is not set.")


async def _api_request(
    method: str, endpoint: str, params: dict[str, Any] | None = None, json_data: dict[str, Any] | None = None
) -> dict[str, Any]:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    url = f"{API_URL}{endpoint}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, headers=headers, params=params, json=json_data)
            if response.is_success:
                if response.status_code == 204:
                    return {"success": True, "details": None}

                try:
                    return {"success": True, "details": response.json()}
                except ValueError:
                    return {"success": True, "details": None}

            if response.status_code in (400, 422):
                try:
                    error_data = response.json()
                except ValueError:
                    error_data = response.text
                return {
                    "success": False,
                    "error": "Validation Error",
                    "status_code": response.status_code,
                    "details": error_data,
                }

            if response.status_code == 401:
                raise RuntimeError("Wrong API key.")

            return {
                "success": False,
                "error": "HTTP Error",
                "status_code": response.status_code,
                "details": response.text,
            }
    except Exception as e:
        return {"success": False, "error": "Network or Internal Error", "details": str(e)}


@mcp.tool("forkflux_list_roles")
async def list_roles():
    """
    Returns a list of available agent roles.

    Use this when you are a Source Agent preparing to publish a new job
    and need to know which roles (e.g., 'qa', 'refactorer', 'security')
    are available to handle specific types of jobs.

    CRITICAL: Output the result as a clean, human-readable Markdown list. DO NOT dump raw JSON.
    """
    return await _api_request("GET", "/agents/roles")


@mcp.tool("forkflux_create_job")
async def create_job(
    summary: str,
    context_payload: dict[str, Any],
    target_role_key: str,
    constraints: list[str],
    artifacts: list[JobArtifact],
    priority: JobPriorityEnum,
    parent_job_id: int | None = None,
):
    """
    Publishes a new handoff job to the ForkFlux coordination bus for delegation.

    CRITICAL: The Target Agent operates in complete isolation. They cannot see your
    local workspace, files, or chat history. You MUST pack all necessary context
    into the parameters below.

    Args:
        summary: A concise, human-readable title of the job.
        context_payload: A highly detailed, structured JSON dictionary. Do NOT pass a simple flat string.
            Include relevant code snippets, error logs, state descriptions, and steps to reproduce.
        target_role_key: The required specialization for this job. MUST be a valid key
            retrieved using the `list_roles` tool (e.g., 'qa_agent', 'security_reviewer').
        constraints: A list of strict acceptance criteria or execution boundaries the Target Agent must follow.
        artifacts: A list of external resources (like S3 URIs, Git commits, or database dumps) attached to this job.
        priority: The urgency of the job.
        parent_job_id: (Optional) The ID of the job that spawned this job, used for tracing the handoff chain.
    """
    serialized_artifacts = [artifact.model_dump() for artifact in artifacts] if artifacts else []

    return await _api_request(
        "POST",
        "/jobs",
        json_data={
            "summary": summary,
            "context_payload": context_payload,
            "target_role_key": target_role_key,
            "constraints": constraints,
            "artifacts": serialized_artifacts,
            "priority": priority,
            "parent_job_id": parent_job_id,
        },
    )


@mcp.tool("forkflux_list_jobs")
async def list_jobs(
    limit: Annotated[int, Field(default=50, ge=1, le=200)] = 50,
    status: JobStatusEnum | None = JobStatusEnum.PUBLISHED,
    target_role_key: str | None = None,
    my_role_only: bool = True,
):
    """
    Fetches a list of jobs from the ForkFlux Coordination Bus.
    Target Agents should use this tool to poll the Coordination Bus for available jobs to claim.

    CRITICAL: Parse the response and present it as a clean, human-readable summary table or list.
    DO NOT output the raw JSON to the user, as context payloads are too large.

    Args:
        limit: The maximum number of jobs to return (min 1, max 200). Default is 50.
        status: Filter by job lifecycle status. Defaults to 'published' (jobs ready to be claimed).
        target_role_key: Filter jobs explicitly intended for a specific agent role.
        my_role_only: If True (default), filters the pool to return only jobs matching the current agent's role.
    """
    return await _api_request(
        "GET",
        "/jobs",
        params={
            "limit": limit,
            "status": status.value if status else None,
            "target_role_key": target_role_key,
            "my_role_only": my_role_only,
        },
    )


@mcp.tool("forkflux_job_details")
async def get_job_details(job_id: Annotated[int, Field(description="The unique numeric ID of the job to retrieve.")]):
    """
    Fetches the detailed card and full handoff context for a specific job without claiming it.

    NOTE: You do NOT need to call this after `forkflux_claim_job`, because claiming automatically
    returns the full context. Use this only if you need to inspect a job before deciding to claim it.

    Args:
        job_id: The ID of the job.
    """
    return await _api_request("GET", f"/jobs/{job_id}")


@mcp.tool("forkflux_claim_job")
async def claim_job(job_id: Annotated[int, Field(description="The unique ID of the job to claim.")]):
    """
    Atomically claims a published job from the ForkFlux coordination bus and returns its FULL context.

    Target Agents MUST call this tool immediately after deciding to take a job.
    Claiming transitions the job status to 'in_progress' and locks it for you.

    If the claim fails (e.g., returns an HTTP 409 Conflict error), it means
    another agent has already claimed this job. Do not proceed with the work;
    instead, fetch the list of jobs again to find a new one.

    Args:
        job_id: The ID of the job you want to lock and claim for yourself.
    """
    return await _api_request("POST", f"/jobs/{job_id}/claim")


@mcp.tool("forkflux_change_job_status")
async def change_job_status(
    job_id: Annotated[int, Field(description="The unique ID of the job.")],
    status: JobChangeStatusEnum,
    failure_reason: Annotated[
        str | None,
        Field(
            description="A detailed explanation of why the job failed. REQUIRED if status is 'failed' otherwise ignore."
        ),
    ] = None,
):
    """
    Updates the execution lifecycle status of a job you have claimed.

    Target Agents MUST use this tool to reflect their current progress:
    1. 'in_progress': Set this if the job was 'claimed' but not automatically marked as 'in_progress'.
    2. 'completed': Set this ONLY when you have successfully finished the job and met ALL acceptance criteria.
    3. 'failed': Set this if an unrecoverable error occurs. You MUST populate `failure_reason`.
    4. 'cancelled': Set this if the user explicitly asks you to abort.
    """
    return await _api_request(
        "POST", f"/jobs/{job_id}/status", json_data={"status": status.value, "failure_reason": failure_reason}
    )


@mcp.prompt("list-available-jobs")
def list_available_jobs_prompt():
    """
    Fetch the current list of available jobs from ForkFlux.
    Use this prompt to see the pool of tasks ready for execution.
    """
    return """
    You are working with ForkFlux. Your current goal is to find available work.

    1. Call the `forkflux_list_jobs` tool.
    2. Analyze the list:
       - If there are no jobs, inform the user.
       - If there are jobs, display the list with job id, summary, status, and priority. DO NOT dump raw JSON.
       - Ask the user to select a task to claim.

    Important: Follow the ForkFlux protocol for atomic operations.
    """


if __name__ == "__main__":
    mcp.run()
