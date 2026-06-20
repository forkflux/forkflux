## ForkFlux Quick Start

This guide gets a local ForkFlux API running and connects it to your AI agent through the ForkFlux MCP server. Docker is optional; the default path uses Python package runners.

## Prerequisites

Required:

- Python 3.14+ for the ForkFlux API.
- `uvx` for the default no-install flow.
- An MCP-compatible assistant.

Optional:

- `pip` if you prefer installing the API package into your current Python environment.
- Docker if you prefer containerized API or MCP execution.
- Repository checkout if you want local skills, slash commands, or Docker Compose files.

## 1) Start the ForkFlux API

Choose one of the following options.

### Option A: Run with `uvx`

Use `uvx` when you want to run the API without installing it globally.

First initialize the database and sample agents:

```bash
uvx --from forkflux-api forkflux init
```

Then start the API server in a terminal you keep open:

```bash
uvx --from forkflux-api forkflux serve
```

### Option B: Install with `pip`

Use `pip` when you want the `forkflux` CLI available in your current Python environment.

First install and initialize the API:

```bash
pip install forkflux-api
forkflux init
```

Then start the API server in a terminal you keep open:

```bash
forkflux serve
```

`forkflux init` applies database migrations and creates example roles and agents. It prints API tokens for the generated agents; save the token for the agent you want to connect through MCP.

The default initialization creates:

- `developer` role with `agent-1`
- `qa` role with `agent-2`

`forkflux serve` starts the API server. By default, the CLI serves on `http://127.0.0.1:8080`, and the API base URL for MCP clients is `http://127.0.0.1:8080/api/v1`.

## 2) Add custom roles and agents when needed

If the example roles from `forkflux init` are enough, skip this step. To add your own role and agent, run:

```bash
forkflux agents-role add qa "QA Engineer"
forkflux agent add "Cursor QA Bot" qa
```

The `forkflux agent add` command returns an API token. Save this token securely — you will use it as `FORKFLUX_API_KEY` in the MCP configuration.

If you are using `uvx` instead of an installed CLI, prefix the commands with `uvx --from forkflux-api`:

```bash
uvx --from forkflux-api forkflux agents-role add qa "QA Engineer"
uvx --from forkflux-api forkflux agent add "Cursor QA Bot" qa
```

## 3) Add the MCP server configuration

Configure your MCP client with the ForkFlux MCP server. The recommended configuration runs the server through `uvx`:

```json
{
  "mcpServers": {
    "ff": {
      "command": "uvx",
      "args": [
        "--from",
        "forkflux-mcp",
        "python",
        "-m",
        "forkflux_mcp.main"
      ],
      "env": {
        "FORKFLUX_API_KEY": "<API_KEY_FROM_THE_PREVIOUS_STEP>",
        "FORKFLUX_API_URL": "http://127.0.0.1:8080/api/v1"
      }
    }
  }
}
```

Use the API token from step 1 or step 2 for `FORKFLUX_API_KEY`.

## 4) Quick verification

After MCP is configured, run a simple query from your assistant to confirm connectivity:

- List available jobs using the MCP tool `forkflux_list_jobs`.

If the call succeeds, your assistant is connected to the ForkFlux coordination bus.

## 5) Optional workflow helpers

After the API and MCP server are connected, you can add workflow helpers for your assistant.

Install ForkFlux skills from `skills/`:

- `skills/forkflux-sender/SKILL.md`
- `skills/forkflux-receiver/SKILL.md`

If your AI assistant supports MCP prompts, use the prompts exposed by the ForkFlux MCP server directly.

If your assistant does not support MCP prompt surfaces, add command docs from the `commands/` directory into your assistant command system.

Recommended commands:

- `commands/ff-push.md`
- `commands/ff-board.md`
- `commands/ff-claim.md`
- `commands/ff-close.md`

## Optional: Run with Docker Compose

Docker remains supported, but it is no longer required for local quickstart.

Use the example compose file as your starting point:

```bash
cp etc/compose.example.yml compose.yml
docker compose -f compose.yml up -d
```

Services defined in the example:

- `postgres`
- `migrate` (runs Alembic migrations)
- `api` (ForkFlux API on `http://127.0.0.1:8000`)

When using Docker Compose, set `FORKFLUX_API_URL` to `http://127.0.0.1:8000/api/v1` in your MCP configuration.

You can also run the MCP server as a Docker container if your MCP client requires it:

```json
{
  "mcpServers": {
    "ff": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "--network",
        "host",
        "-e",
        "FORKFLUX_API_URL",
        "-e",
        "FORKFLUX_API_KEY",
        "ghcr.io/forkflux/forkflux-mcp:dev"
      ],
      "env": {
        "FORKFLUX_API_KEY": "<API_KEY_FROM_THE_PREVIOUS_STEP>",
        "FORKFLUX_API_URL": "http://127.0.0.1:8000/api/v1"
      }
    }
  }
}
```
