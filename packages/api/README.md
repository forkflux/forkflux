# ForkFlux

> Core server for ForkFlux, the self-hosted multi-agent collaboration and audit layer for AI-assisted engineering teams.

ForkFlux is the stateful, self-hosted coordination and audit layer behind ForkFlux. It gives engineering teams and their isolated AI agents a shared, machine-readable system for delegating work, retaining handoff context and artifacts, tracking dependencies and lifecycle transitions, and recording the outcome of each job.

Use this package when you need the ForkFlux service itself: a FastAPI application backed by PostgreSQL or SQLite, a bundled dashboard when built assets are present, and a CLI for database initialization, server startup, role and agent management, job inspection, and metrics.

## What it provides

- **Shared, auditable job queue** for agent-to-agent work delegation.
- **Atomic claims** so only one agent can own a published job at a time.
- **Structured handoffs** through context payloads, constraints, and artifacts.
- **Lifecycle and dependency tracking** for published, pending, in-progress, blocked, completed, failed, and cancelled work.
- **Job revision and retry workflows**, including rejection records and focused reopen context.
- **Role-aware routing**, agent identity, and API-token management.
- **Dashboard-facing endpoints** for jobs, agents, roles, and the active profile.

## Package

```bash
pip install forkflux
```

The installed CLI entry point is:

```bash
forkflux --help
```

Common commands:

```bash
forkflux init                 # apply database migrations
forkflux serve                # run the API on 0.0.0.0:8000
forkflux stats                # show recent queue and handoff metrics
forkflux agents-role list     # list configured target roles
forkflux agent list           # list registered agents and roles
forkflux job list             # inspect jobs from the CLI
```

`forkflux quickstart` is the automated local demo command. It creates example roles and agents, installs workflow helpers, and registers MCP servers with two detected supported assistant CLIs. Use the main repository documentation for the complete quickstart and manual setup paths.

## Configuration and API

Set `DATABASE_URL` to use a specific database. The API accepts `sqlite+aiosqlite` and PostgreSQL URLs. Without it, the CLI uses SQLite and resolves the database from the current project (`.forkflux/forkflux.db`) or the platform's application-data directory.

The FastAPI application is exposed as `forkflux_api.main:app`. Its default base URL is `http://127.0.0.1:8000`; API routes are under `/api/v1`, with separate `/mcp` and `/ui` route groups. The health endpoint is `GET /api/v1/health` and returns HTTP 204.

For endpoint schemas and authenticated MCP workflows, see the [API reference](https://docs.forkflux.ai/api-reference) and [MCP integration guide](https://docs.forkflux.ai/mcp-integration).

## Development

From this directory:

```bash
uv sync
uv run pytest tests/test_health.py -v
```

The test suite separates service unit tests from repository and endpoint integration tests. PostgreSQL-backed integration tests use the repository's test fixtures and testcontainers configuration.

## Runtime requirements

- Python 3.14+

See the main ForkFlux repository for local Docker setup, MCP integration, and end-to-end handoff examples.
