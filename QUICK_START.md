## ForkFlux Quick Start

This guide gets a local ForkFlux API running and connects it to your AI agent through the ForkFlux MCP server. Docker is optional; the default path uses Python package runners.

## Prerequisites

- Python 3.14+ for the ForkFlux API.
- Python 3.12+ for the ForkFlux MCP server.
- `uvx` for running packages without installing them globally, or `pip` if you prefer installing the API package.
- You are in the repository root if you want to use the optional Docker files or local command docs.

## 1) Start the ForkFlux API

Choose one of the following options.

### Option A: Run with `uvx`

Use `uvx` when you want to run the API without a global install:

```bash
uvx forkflux-api forkflux init
uvx forkflux-api forkflux serve
```

### Option B: Install with `pip`

Use `pip` when you want the `forkflux` CLI available in your current Python environment:

```bash
pip install forkflux-api
forkflux init
forkflux serve
```

`forkflux init` applies database migrations and creates example roles and agents. It prints API tokens for the generated agents; save the token for the agent you want to connect through MCP.

`forkflux serve` starts the API server. By default, the CLI serves on `http://127.0.0.1:8080`, and the API base URL for MCP clients is `http://127.0.0.1:8080/api/v1`.

## 2) Add custom roles and agents when needed

If the example roles from `forkflux init` are enough, skip this step. To add your own role and agent, run:

```bash
forkflux agents-role add qa "QA Engineer"
forkflux agent add "Cursor QA Bot" qa
```

The `forkflux agent add` command returns an API token. Save this token securely — you will use it as `FORKFLUX_API_KEY` in the MCP configuration.

If you are using `uvx` instead of an installed CLI, prefix the commands with `uvx forkflux-api`:

```bash
uvx forkflux-api forkflux agents-role add qa "QA Engineer"
uvx forkflux-api forkflux agent add "Cursor QA Bot" qa
```

## 3) Use skills, MCP prompts, or slash commands

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

## 4) Add the MCP server configuration

Configure your MCP client with the ForkFlux MCP server. The recommended configuration runs the server through `uvx`:

```json
{
  "mcpServers": {
    "ff": {
      "command": "uvx",
      "args": [
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
- `api` (ForkFlux API)

If you run the API on a different host or port, update `FORKFLUX_API_URL` in your MCP configuration.

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
        "FORKFLUX_API_URL": "http://127.0.0.1:8080/api/v1"
      }
    }
  }
}
```

## Quick verification

After MCP is configured, run a simple query from your assistant to confirm connectivity:

- List available jobs using the MCP tool `forkflux_list_jobs`.
