from typing import AsyncGenerator

import pytest_asyncio
from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport
from src.main import mcp


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[Client[FastMCPTransport], None]:
    async with Client(transport=mcp) as mcp_client:
        yield mcp_client
