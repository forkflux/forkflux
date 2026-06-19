# ForkFlux API

> Core API server and coordination bus for cross-device AI agent task handoff.

ForkFlux API is the stateful coordination layer behind ForkFlux. It gives isolated AI agents a shared, machine-readable job pool for publishing work, atomically claiming tasks, transferring context and artifacts, and closing jobs with explicit lifecycle states.

Use this package when you need the ForkFlux coordination bus service itself: a FastAPI application backed by PostgreSQL, plus a small CLI for registering target roles and agent API tokens.

## What it provides

- **Shared handoff queue** for agent-to-agent job delegation.
- **Atomic claims** so only one agent can own a published job.
- **Structured context transfer** through job constraints, payloads, and artifacts.
- **Lifecycle control** for `published` → `in_progress` → `completed` / `failed` / `cancelled`.
- **Agent identity and role registry** for role-aware routing.

## Package

```bash
pip install forkflux-api
```

The installed CLI entry point is:

```bash
forkflux --help
```

## Runtime requirements

- Python 3.14+
- PostgreSQL reachable through `DATABASE_URL`

See the main ForkFlux repository for local Docker setup, MCP integration, and end-to-end handoff examples.
