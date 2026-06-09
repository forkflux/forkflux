import os
from typing import Any

import httpx
from fastmcp import FastMCP

FORKFLUX_INSTRUCTIONS = """
You are connected to the ForkFlux Coordination Bus, an infrastructure layer for decentralized AI agents to securely hand off jobs across isolated machines.

Depending on your current role in the user's workflow, follow these rules:

AS A SOURCE AGENT (Publishing work):
- When a job requires execution by another agent (e.g., passing code to a QA agent), use `forkflux_create_job`.
- To get all available roles, use `forkflux_list_roles`.
- Provide explicit, strict `constraints` and embed all necessary context in the `context_payload` and all necessary artifacts in the `artifacts`.

AS A TARGET AGENT (Consuming work):
1. Use `forkflux_list_jobs` to find available jobs with status 'published'.
2. Verify with the user that the job is safe to claim (unless the user has pre-approved autonomous claiming).
3. Attempt to claim a job using `forkflux_claim_job`.
4. EXTREMELY IMPORTANT: If the claim fails with a "409 Conflict" (Job already claimed), DO NOT complain to the user or stop. Silently fetch the list again and try claiming the next available job.
5. Once claimed, read the full context via `forkflux_get_job_context`.
6. Complete the work locally, then update the status to 'completed' or 'failed' (include a failure_reason if it failed) using `forkflux_update_status`.
"""  # noqa: E501

mcp = FastMCP(
    "ForkFlux",
    instructions=FORKFLUX_INSTRUCTIONS,
)


API_URL = os.environ.get("FORKFLUX_API_URL", "http://localhost:8000/api/v1")
API_KEY = os.environ.get("FORKFLUX_API_KEY")

if not API_KEY:
    print("Warning: FORKFLUX_API_KEY is not set.")


def _api_request(
    method: str, endpoint: str, params: dict[str, Any] | None = None, json_data: dict[str, Any] | None = None
) -> dict[str, Any]:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    url = f"{API_URL}{endpoint}"

    try:
        with httpx.Client() as client:
            response = client.request(method, url, headers=headers, params=params, json=json_data)
            if response.is_success:
                return {"success": True, "details": response.json()}

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
def list_roles():
    """
    Returns a list of available agent roles.

    Use this when you are a Source Agent preparing to publish a new job
    and need to know which roles (e.g., 'qa', 'refactorer', 'security')
    are available to handle specific types of tasks.
    """
    return _api_request("GET", "/agents/roles")


if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=9000, docs_url="/docs")
