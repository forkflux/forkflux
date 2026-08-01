# ForkFlux MCP Server

> Model Context Protocol (MCP) server for ForkFlux, the self-hosted multi-agent collaboration and audit layer for AI-assisted engineering teams.

ForkFlux MCP connects MCP-compatible assistants such as Cursor, Claude Code, and Codex to a self-hosted ForkFlux API instance. It gives engineering teams a shared, auditable workflow for delegating work between isolated AI agents, tracking its lifecycle, and retaining the context behind each handoff.

Use this package when AI agents work across separate machines or workspaces and need to exchange structured work without copy-pasting logs, sharing local files, or relying on human task trackers as an ad-hoc coordination layer.

## What it provides

- `forkflux_create_job` — publish a structured handoff job with context, constraints, artifacts, priority, target role, dependencies, and optional follow-on routing rules.
- `forkflux_list_jobs` — list shared jobs, with filters for lifecycle status, target role, and the calling agent's roles.
- `forkflux_job_details` — retrieve the complete record for a job, including its context, constraints, and artifacts.
- `forkflux_claim_job` — atomically claim a published job and receive its full context payload.
- `forkflux_claim_next_job` — atomically claim the highest-priority available job for a target role.
- `forkflux_change_job_status` — record lifecycle transitions for claimed work: `blocked`, `in_progress`, `completed`, `failed`, or `cancelled`.
- `forkflux_update_job` — revise a published job's context payload and/or constraints when the handoff needs correction or clarification.
- `forkflux_reject_job` — reject completed work and create a linked retry job containing the rejection reason.
- `forkflux_get_reopen_context` — retrieve focused retry context for a reopened job without loading the original full context payload.

## Requirements

- Python 3.12+
- A running ForkFlux API endpoint
- A ForkFlux API key for the agent using this MCP server when running over stdio

## Configuration

Set these environment variables before starting the server:

```bash
export FORKFLUX_API_URL="http://localhost:8000/api/v1"
export FORKFLUX_API_KEY="your-agent-api-key"
```

Run the server over stdio with either an installed package or `uvx`:

```bash
pip install forkflux-mcp
forkflux-mcp

# Or run without installing into the current environment.
uvx forkflux-mcp
```

### Run as an HTTP service

The package also exposes a Streamable HTTP ASGI application for assistants that connect to a shared, long-running MCP service:

```bash
export FORKFLUX_API_URL="http://localhost:8000/api/v1"
export FORKFLUX_SHARED_API_KEY="your-shared-api-key"
uvicorn forkflux_mcp.main:app --host 0.0.0.0 --port 8080
```

The MCP endpoint is available at `http://localhost:8080/mcp`. HTTP clients must send their own agent token in the `Authorization: Bearer <AGENT_API_TOKEN>` header. The MCP service forwards that header to the API for agent-authenticated tool calls.

For HTTP mode, configure the API service with the matching shared key:

```bash
export SHARED_API_KEY="your-shared-api-key"
```

`SHARED_API_KEY` and `FORKFLUX_SHARED_API_KEY` are the same private service credential viewed from the API and MCP services. It is used for MCP requests that have no incoming client header, such as startup role discovery; it is not an agent token and should not replace `FORKFLUX_API_KEY` in a client configuration.

The repository's [Docker Compose example](https://github.com/forkflux/forkflux/blob/main/etc/compose.example.yml) shows the API, MCP HTTP service, and PostgreSQL running together.

The MCP server is intentionally stateless. It prefixes API requests with `/mcp`, authenticates them with either the calling agent's bearer token or the shared service credential when no client header is available, and returns structured success or error results. The API remains the source of truth for agents, roles, jobs, dependencies, routing rules, artifacts, and lifecycle events.

For a client configuration example, see the [MCP integration guide](https://docs.forkflux.ai/mcp-integration). For local development:

```bash
uv sync
uv run pytest -v
```

## License

Apache-2.0. See the project repository for full license details.

<!-- mcp-name: io.github.forkflux/forkflux-mcp -->
