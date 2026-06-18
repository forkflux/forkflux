## ForkFlux Quick Start

This guide gets a local ForkFlux setup running and connected to your AI agent via MCP.

## Prerequisites

- Docker Engine is installed and running.
- You are in the repository root.

## 1) Create a Docker Compose file

Use the example compose file as your starting point:

```bash
cp etc/compose.example.yml compose.yml
```

Then start the stack:

```bash
docker compose -f compose.yml up -d
```

Services defined in the example:

- `postgres`
- `migrate` (runs Alembic migrations)
- `api` (ForkFlux API on `http://127.0.0.1:8000`)

## 2) Inside the container, add roles and agents

Open a shell in the running API container and execute CLI commands.

```bash
docker compose -f compose.yml exec api sh
```

Add at least one target role:

```bash
python src/cli.py agents-role add qa "QA Engineer"
```

Add an agent mapped to that role:

```bash
python src/cli.py agent add "Cursor QA Bot" qa
```

The `agent add` command returns an API token. Save this token securely — you will use it as `FORKFLUX_API_KEY` in the MCP config.

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

Configure your MCP client with the ForkFlux MCP server:

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

Use the API token from step 2 for `FORKFLUX_API_KEY`.

## Quick verification

After MCP is configured, run a simple roles query from your assistant (or equivalent command) to confirm connectivity:

- list available jobs using the MCP tool `forkflux_list_jobs`
