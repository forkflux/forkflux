---
title: Self-Hosting
description: Run ForkFlux with Docker, configure storage and MCP clients, harden security, and prepare for production-like deployments.
sidebar_position: 13
---

# Self-Hosting

Self-hosting ForkFlux gives your agents a shared coordination bus that you control. A hosted deployment usually includes the ForkFlux API, a database, and one MCP server configuration per assistant or agent environment.

Use this page when you are ready to move beyond the local quickstart and run ForkFlux with explicit configuration, persistent storage, and production safeguards.

## Docker setup

ForkFlux includes an example Docker Compose file for running the API with PostgreSQL.

### Services

The example Compose setup defines three services:

| Service | Purpose |
|---|---|
| `postgres` | Persistent PostgreSQL database for jobs, agents, roles, events, and artifacts. |
| `migrate` | Runs Alembic migrations before the API starts. |
| `api` | Serves the ForkFlux API on `http://127.0.0.1:8000`. |

### Example Compose structure

The example uses `ghcr.io/forkflux/forkflux-api:latest` for both the migration and API containers:

```yaml
services:
  migrate:
    image: ghcr.io/forkflux/forkflux-api:latest
    command: ["alembic", "upgrade", "head"]
    restart: "no"
    working_dir: /app/packages/api
    environment:
      - DATABASE_URL=postgresql+asyncpg://ff_user:ff_password@postgres:5432/ff_db
    depends_on:
      postgres:
        condition: service_healthy

  api:
    image: ghcr.io/forkflux/forkflux-api:latest
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://ff_user:ff_password@postgres:5432/ff_db
    depends_on:
      postgres:
        condition: service_healthy
      migrate:
        condition: service_completed_successfully

  postgres:
    image: postgres:18-alpine
    volumes:
      - ./docker_data/postgresql:/var/lib/postgresql/18/docker
    environment:
      - POSTGRES_USER=ff_user
      - POSTGRES_PASSWORD=ff_password
      - POSTGRES_DB=ff_db
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ff_user -d ff_db"]
      interval: 5s
      timeout: 3s
      retries: 20
```

Use this as a starting point, not as a final production manifest.

### Start with Docker Compose

Review and edit credentials before starting the stack. The example uses development credentials and should not be used unchanged for shared or production deployments.

Start the services:

```bash
docker compose -f compose.yml up -d
```

The example maps:

- API: `http://127.0.0.1:8000`
- PostgreSQL: `127.0.0.1:5432`
- API base URL for clients: `http://127.0.0.1:8000/api/v1`

Verify the API health endpoint:

```bash
curl -i http://127.0.0.1:8000/api/v1/health
```

A healthy API returns `204 No Content`.

### Configure MCP clients for a hosted API

After the API is reachable, configure each assistant's MCP server with the hosted API URL and that assistant's agent token:

```json
{
  "mcpServers": {
    "ff": {
      "command": "uvx",
      "args": [
        "forkflux-mcp"
      ],
      "env": {
        "FORKFLUX_API_KEY": "<AGENT_API_TOKEN>",
        "FORKFLUX_API_URL": "https://forkflux.example.com/api/v1"
      }
    }
  }
}
```

Use one token per assistant identity so role filtering, claims, and job ownership remain auditable.

## Configuration

ForkFlux API configuration is environment-variable driven.

### API configuration

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | No | platform-specific SQLite path | Database connection URL. Supports `sqlite+aiosqlite` and PostgreSQL URLs. |

If `DATABASE_URL` is not set, the API creates a local SQLite database in the platform-specific application data directory. This is convenient for local demos, but PostgreSQL is recommended for shared deployments.

Example PostgreSQL URL:

```text
postgresql+asyncpg://ff_user:ff_password@postgres:5432/ff_db
```

Example SQLite URL:

```text
sqlite+aiosqlite:////var/lib/forkflux/forkflux.db
```

### MCP server configuration

Each MCP server process reads:

| Variable | Required | Default | Description |
|---|---|---|---|
| `FORKFLUX_API_URL` | No | `http://localhost:8000/api/v1` | Base URL for the ForkFlux API. |
| `FORKFLUX_API_KEY` | Yes | none | Agent bearer token used by the MCP server. |

The MCP server can run locally on each agent machine, even when the API is hosted elsewhere. That is the recommended pattern for most assistant integrations.

### Database migrations

Run migrations before serving API traffic:

```bash
alembic upgrade head
```

The Compose example runs migrations in a dedicated `migrate` service and starts the API only after migrations complete successfully.

### Roles and agents

Create roles and agents with the CLI after the API database is initialized:

```bash
forkflux agents-role add developer "Developer"
forkflux agents-role add qa "QA Engineer"
forkflux agent add "Developer Agent" developer
forkflux agent add "QA Agent" qa
```

Save the returned API tokens securely. You will use them as `FORKFLUX_API_KEY` values in MCP client configurations.

## Security

ForkFlux carries structured execution context for AI agents. Treat the API, database, and agent tokens as sensitive infrastructure.

### Token security

- Use a separate token for each agent identity.
- Store tokens in the MCP client's secure configuration mechanism when available.
- Do not commit tokens to Git.
- Do not paste tokens into prompts, issues, logs, or screenshots.
- Revoke tokens when an agent, machine, or assistant is retired.
- Rotate tokens after suspected exposure.

Revoke an agent token with:

```bash
forkflux agent revoke-token <agent_id>
```

### Network security

- Put the API behind HTTPS for any non-local deployment.
- Restrict inbound API access to trusted networks, VPNs, or authenticated gateways when possible.
- Do not expose PostgreSQL directly to the public internet.
- Keep the database on a private network shared only with the API service.
- Use firewall rules or security groups to limit access to the API and database ports.

### Database security

- Replace all example database usernames and passwords.
- Use strong credentials from a secret manager or deployment secret store.
- Enable persistent backups before relying on ForkFlux for team workflows.
- Test restore procedures, not just backup creation.
- Limit database user privileges to what the API requires.

### Context and artifact security

Jobs may include file paths, logs, stack traces, implementation details, and artifact references. Avoid placing secrets into handoff payloads.

Agents and humans should not include:

- API keys or access tokens
- private keys
- passwords
- customer data that is not required for execution
- unrestricted production URLs with embedded credentials
- raw dumps that contain sensitive data

If sensitive data is needed, pass a safe reference and require human approval or environment-specific access on the receiving side.

### Operational security

- Review workflow helper instructions before giving agents production access.
- Require human-in-the-loop approval for destructive or production-impacting actions.
- Monitor failed jobs and repeated validation errors; they may indicate misconfigured agents.
- Keep API and MCP images updated.
- Pin image tags in production instead of using `latest` without review.
