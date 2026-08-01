from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest_asyncio
from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport
from forkflux_mcp.main import mcp

ROLES_PAYLOAD = {
    "success": True,
    "details": [
        {"role_key": "qa_agent", "role_label": "QA Agent"},
        {"role_key": "security_reviewer", "role_label": "Security Reviewer"},
    ],
}


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[Client[FastMCPTransport], None]:
    # The MCP lifespan fetches the available roles from the API before registering
    # the role-dependent tools. Mock that bootstrap request so the dynamic
    # TargetRoleEnum is populated deterministically for every test.
    with patch("forkflux_mcp.main._api_request", return_value=ROLES_PAYLOAD):
        async with Client(transport=mcp) as mcp_client:
            yield mcp_client
