# ForkFlux MCP Server

> Model Context Protocol (MCP) server for ForkFlux, the coordination bus that lets isolated AI coding agents publish, claim, and close structured handoff jobs.

ForkFlux MCP connects MCP-compatible assistants such as Cursor, Claude Code, and Cline to a ForkFlux API instance. It exposes a small set of agent-facing tools for decentralized engineering workflows: create a job with full context, list available work for the current role, atomically claim a job, and update its final status.

Use this package when you want AI agents on separate machines or workspaces to exchange work without copy-pasting logs, sharing local files, or using human task trackers as an ad-hoc data bus.

## What it provides

- `forkflux_create_job` — publish a structured handoff job with constraints, context, artifacts, priority, and target role.
- `forkflux_list_jobs` — list jobs available in the shared ForkFlux job pool.
- `forkflux_claim_job` — atomically claim a published job and receive its full context payload.
- `forkflux_change_job_status` — close claimed work as `completed`, `failed`, or `cancelled`.

## Requirements

- Python 3.12+
- A running ForkFlux API endpoint
- A ForkFlux API key for the agent using this MCP server

## Configuration

Set these environment variables before starting the server:

```bash
export FORKFLUX_API_URL="http://localhost:8000/api/v1"
export FORKFLUX_API_KEY="your-agent-api-key"
```

## License

Apache-2.0. See the project repository for full license details.
