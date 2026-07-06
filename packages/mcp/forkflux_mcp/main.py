import asyncio
import os
from enum import Enum
from typing import Annotated, Any

import httpx
from fastmcp import FastMCP
from pydantic import Field

from forkflux_mcp.constants import JobChangeStatusEnum, JobPriorityEnum, JobStatusEnum
from forkflux_mcp.schemas import JobArtifact

FORKFLUX_INSTRUCTIONS = """
You are connected to the ForkFlux Coordination Bus, an infrastructure layer for decentralized AI agents to securely hand off jobs across isolated machines.

You do not have a fixed role. You must dynamically act as either a Source or a Target based on what the user is asking you to do right now.

WHEN THE USER ASKS YOU TO HAND OFF WORK (Acting as Source):
- When a job requires execution by another agent (e.g., passing code to a QA agent), use `forkflux_create_job`.
- Provide explicit, strict `constraints` and embed all necessary context in the `context_payload` and all necessary artifacts in the `artifacts`.

WHEN THE USER ASKS YOU TO CHECK FOR OR RECEIVE NEW WORK (Acting as Target):
1. Use `forkflux_list_jobs` to find available jobs with status 'published'.
2. Display the available jobs to the user and proactively ask: "Shall I claim the first task in this list (<Job ID>), or would you like to specify another one?"
3. Wait for the user's response. Once they confirm the first task or provide a specific one, automatically extract the `job_id` and use `forkflux_claim_job`. This tool will return the FULL context payload immediately (Fat Claim).
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


async def get_dynamic_roles_enum() -> Enum:
    list_available_roles = await _api_request("GET", "/agents/roles")
    if list_available_roles["success"]:
        available_roles = [x["role_key"] for x in list_available_roles["details"]]
    else:
        available_roles = []
    return Enum("TargetRoleEnum", {role: role for role in available_roles})


TargetRoleEnum = asyncio.run(get_dynamic_roles_enum())


@mcp.tool("forkflux_create_job")
async def create_job(
    summary: str,
    context_payload: dict[str, Any],
    target_role_key: TargetRoleEnum,  # type: ignore[valid-type]
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
        target_role_key: The required specialization for this job.
        constraints: A list of strict constraints or execution boundaries the Target Agent must follow.
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
            "target_role_key": target_role_key.value,  # type: ignore[attr-defined]
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
    target_role_key: TargetRoleEnum | None = None,  # type: ignore[valid-type]
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
        "/jobs?order=priority_desc&order=created_at_asc",
        params={
            "limit": limit,
            "status": status.value if status else None,
            "target_role_key": target_role_key.value if target_role_key else None,  # type: ignore[attr-defined]
            "my_role_only": my_role_only,
        },
    )


@mcp.tool("forkflux_job_details")
async def job_details(job_id: Annotated[int, Field(description="The unique ID of the job.")]):
    """
    Fetches full details of a job by ID, including context payload, constrains, and artifacts.

    Args:
        job_id: The ID of the job to retrieve.
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

    Claiming a job automatically transitions it to 'in_progress'.
    Target Agents should use this tool for manual transitions only:
    1. 'completed': Set this ONLY when you have successfully finished the job and met ALL constraints.
    2. 'failed': Set this if an unrecoverable error occurs. You MUST populate `failure_reason`.
    3. 'cancelled': Set this if the user explicitly asks you to abort.
    """
    return await _api_request(
        "POST", f"/jobs/{job_id}/status", json_data={"status": status.value, "failure_reason": failure_reason}
    )


@mcp.prompt("board")
def board_prompt() -> str:
    """
    Fetch available published jobs strictly for the agent's current role from the ForkFlux shared pool.
    Use this prompt when the user wants to see the dashboard/board of ready-to-claim tasks.
    """
    return """
    You are an AI Agent operating within the ForkFlux Coordination Bus protocol.
    Your current goal is to fetch and display the board of available tasks waiting for your specific role.

    Follow these instruction steps carefully:

    1. Call the `forkflux_list_jobs` MCP tool with the exact following arguments:
       - `status`: "published"
       - `target_role_key`: null
       - `my_role_only`: true

    2. CRITICAL: Do not modify, omit, or guess these parameters. They are strictly required by the protocol to isolate work meant for your role.

    3. Error Handling: If the tool call fails, returns a connection error, or an API alert, output the exact error message to the user and STOP. Do not hallucinate, imagine, or mock any jobs.

    4. Empty State: If the returned list from the tool is empty, kindly inform the user that there are currently no published tasks available for your role in the ForkFlux shared pool.

    5. Output Formatting (STRICT RULE):
       - NEVER dump raw JSON payloads directly to the user.
       - Parse the JSON response from the tool and present the jobs as a clean, highly readable Markdown table.
       - The table MUST contain the following columns:
         * **Job ID**: Rendered as inline code (e.g., `job_123`) for easy copying.
         * **Priority**: The execution priority value (e.g., 10, 20, 30).
         * **Source / Creator**: Who created the task (if the field is available in the payload).
         * **Summary**: A brief, truncated snippet of the task's `constraints`.
         * **Created**: The exact date and time when the task was published.

    6. Next Step / Tool Chaining: Conclude your response by proactively asking the user:
       "Shall I claim the first task in this list (<Job ID>), or would you like to specify another one?"

    7. Execution Trigger: Wait for the user's response.
       - If the user confirms to take the first task (e.g., says "yes", "go ahead", etc.), automatically extract its `job_id` and call the `forkflux_claim_job` tool.
       - If the user specifies a different task from the list, extract that specific `job_id` and call the `forkflux_claim_job` tool.
    """  # noqa: E501


@mcp.prompt("claim")
def claim_prompt() -> str:
    """
    Atomically claim a specific job from the ForkFlux coordination bus,
    retrieve its full context payload (Fat Claim), and prepare for execution.
    Use this prompt when the user passes a specific job ID to claim and start working on.
    """
    return """
    You are an AI Agent operating within the ForkFlux Coordination Bus protocol.
    Your current goal is to atomically claim a task, lock it to prevent race conditions, and unpack its full context.

    Follow these execution steps carefully:

    1. PRE-CHECK: Verify that a valid `job_id` is available in the user's request.
       - If the `job_id` is missing, stop and explicitly ask the user to provide it, or suggest they run the `board` prompt first to pick a task.

    2. TOOL CALL: Call the `forkflux_claim_job` MCP tool using the provided `job_id`.

    3. RACE CONDITION HANDLING (409 Conflict):
       - CRITICAL: If the tool returns a `409 Conflict` error, it means another agent on a different machine has already snatched this task.
       - DO NOT hallucinate a successful state.
       - Inform the user politely but clearly that the job is already claimed by someone else, and suggest running the `ff_board` prompt to select a new one.

    4. ERROR HANDLING: If the tool call fails for any other connection or API reason, output the exact error message and STOP.

    5. FAT CLAIM ANALYSIS:
       - Upon a successful response, the tool will return the FULL context payload of the job (including constraints, payload artifacts, and internal guidelines).
       - Read, parse, and analyze this payload thoroughly to build your local execution context.

    6. TOOL CHAINING & NEXT STEP:
       - You are now the official owner of this task. Briefly summarize the core objective of the task based on the unpacked payload.
       - Proceed to ask the user for confirmation to begin execution.

    7. OUTPUT FORMATTING (STRICT RULE):
       - NEVER dump raw JSON response payloads directly to the user.
       - Provide a brief, energetic confirmation in Markdown format using the exact structure below:

       🔒 **Job Claimed**: [Insert the `job_id` as inline code] — [Insert a 1-sentence human-readable summary of the objective].
       🚦 **Status**: Confirmed as `IN_PROGRESS` (API payload value: `in_progress`).
       📦 **Context Received**: Confirmed that the task payload and constraints have been successfully unpacked.
       🚀 **Next Action**: Ask the user: *"Shall I start executing this task now?"*
    """  # noqa: E501


@mcp.prompt("close")
def close_prompt() -> str:
    """
    Close a specific ForkFlux job by updating its lifecycle status to a terminal state
    (completed, failed, or cancelled). Use this prompt when finishing execution.
    """
    return """
    You are an AI Agent operating within the ForkFlux Coordination Bus protocol.
    Your current goal is to transition a specific job into its final terminal state, broadcasting this update to the decentralized bus.

    CRITICAL INFRASTRUCTURE RULE: NEVER attempt to use bash, curl, or terminal commands to execute this state transition. You MUST use the provided `forkflux_change_job_status` MCP tool.

    Follow these execution steps carefully:

    1. PRE-CHECK: Ensure you have a valid `job_id` from your active context and the target termination status.

    2. STATUS VALIDATION: Validate that the target status is strictly one of the allowed TERMINAL lifecycle states:
       - `completed`
       - `failed`
       - `cancelled`
       * CRITICAL: Do NOT use this command to transition a job back to `in_progress` or `published`.

    3. STATE GATEKEEPING RULES (Verify before calling the tool):
       - If status is `completed`: Only call this if you have verified that all code is written, tests pass successfully, and every single constraint from the job context payload is fully met.
       - If status is `failed`: Call this if an unrecoverable error occurs, tests persistently fail, environment blockers arise, or constraints cannot be resolved.
       - If status is `cancelled`: Call this if the user explicitly instructs you to abort the execution midway.

    4. MANDATORY ERROR LOGGING: If you are setting the status to `failed`, you MUST populate the `failure_reason` argument with a highly detailed summary. Include stack trace excerpts, logs, or specific unmet constraints so human developers can trace and debug the handoff block.

    5. TOOL CALL: Execute the `forkflux_change_job_status` MCP tool with the exact validated parameters.

    6. TRANSACTION FAILURE HANDLING: If the tool call fails or returns a state-machine transition error from the Coordination Bus, output the exact error message and STOP. Do not hallucinate or assume a successful update.

    7. OUTPUT FORMATTING (STRICT RULE):
       - NEVER dump raw JSON response payloads from the tool directly to the user.
       - Provide a clear, high-visibility status update block in Markdown using the exact structure below:

       🔄 **Job Closed**: [Insert the `job_id` as inline code]
       🚦 **Final State**: `[completed, failed, or cancelled]`
       📝 **Summary / Error Details**:
         - (If completed): [Provide a brief 1-2 sentence human-readable summary of what was implemented to meet the constraints]
         - (If failed): [Print the explicit `failure_reason` that was provided to the tool]
    """  # noqa: E501


@mcp.prompt("push")
def push_prompt() -> str:
    """
    Create and publish a new handoff job into the ForkFlux Coordination Bus.
    Use this prompt when the current agent finishes its task and wants to route the work to another agent/role.
    """
    return """
    You are an AI Agent operating as a Source Agent within the ForkFlux Coordination Bus protocol.
    Your goal is to package the current execution context, artifacts, and strict constraints, and publish them as a new handoff job.

    CRITICAL INFRASTRUCTURE RULE: NEVER attempt to use bash, curl, or terminal commands to issue this API call. You MUST exclusively use the provided ForkFlux MCP tools.

    Follow these execution steps carefully:

    1. TOOL CHAINING (Role Discovery):
       - Analyze available target role keys, match the correct one based on the user's workflow intent, and proceed. Never guess or hallucinate a role key.

    2. PARAMETER PREPARATION (Validate before calling `forkflux_create_job`):
       - `target_role_key`: (String) The exact valid key found via tool chaining.
       - `constraints`: (list[str] / Array of Strings) Explicit constraint entries. Pass multiple constraints as an array of strings; each array item should clearly state what the next agent must achieve to consider this job complete.
       - `context_payload`: (JSON/Dictionary) A highly detailed, structured JSON object. Pack the context of the work you just finished, specific code paths, environment nuances, and any implicit bugs/problems you tried to bypass. CRITICAL: Do NOT pass a simple flat string or raw text block here. It must be a valid structured JSON map.
       - `priority`: (Integer) Must be exactly one of the allowed protocol enums: 10, 20, 30, or 40.
       - `artifacts`: (Array of Objects) List of generated files, diffs, or logs. Only include real, verified files from the current directory. Do not hallucinate hashes, checksums, or non-existent URIs.

    3. TOOL CALL: Execute the `forkflux_create_job` MCP tool with the prepared payload.

    4. ERROR HANDLING: If the tool returns a validation or protocol bus error, output the exact error message and STOP. Do not retry with fake or modified parameters.

    5. OUTPUT FORMATTING (STRICT RULE):
       - Provide a clear, high-visibility status update block in Markdown using the exact structure below.
       - Do NOT dump the raw JSON `context_payload` into the final success chat. Keep it concise.

       🚀 **Job Published**: [Insert the newly created `job_id` as inline code]
       🎯 **Target Role**: [Insert the `target_role_key` as inline code]
       ✅ **Constraints**: [Provide a brief 1-2 sentence human-readable summary of the constraints passed to the next agent]
       📦 **Context Packed**: [Briefly summarize what metadata and technical logs you embedded into the `context_payload`]
    """  # noqa: E501


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
