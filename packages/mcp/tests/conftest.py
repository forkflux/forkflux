from collections.abc import Coroutine
from enum import Enum
from typing import AsyncGenerator
from unittest.mock import patch

import pytest_asyncio
from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport

TargetRoleEnum = Enum(
    "TargetRoleEnum",
    {
        "qa_agent": "qa_agent",
        "security_reviewer": "security_reviewer",
    },
    type=str,
)


def _mock_asyncio_run(coro: Coroutine[object, object, object]) -> type[Enum]:
    coro.close()
    return TargetRoleEnum


with patch("asyncio.run", side_effect=_mock_asyncio_run):
    from src.main import mcp


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[Client[FastMCPTransport], None]:
    async with Client(transport=mcp) as mcp_client:
        yield mcp_client
