---
title: Quick Start
description: Run ForkFlux locally and connect an MCP-compatible AI assistant to the coordination bus.
---

# Quick Start

This guide gets a local ForkFlux API running and connects it to your AI agents through the ForkFlux MCP server. Docker is optional; the default path uses Python package runners.

Use the automated demo path when you want to try ForkFlux locally in a few minutes. Use the manual path when you need explicit control over roles, agents, API tokens, MCP client configuration, or deployment settings.

## What you'll set up

By the end of this guide, you will have:

- a local ForkFlux API server
- at least one registered agent with an API token
- an MCP server configuration that lets your assistant call ForkFlux tools
- a quick connectivity check from your assistant

## Prerequisites

Required:

- Python 3.14+ for the ForkFlux API
- `uvx` for the default no-install flow
- an MCP-compatible assistant

Required for the automated local demo:

- at least two supported local assistant CLIs: Codex, Claude Code, OpenCode, or Hermes

Optional:

- `pip` if you prefer installing the API package into your current Python environment
- Docker if you prefer containerized API or MCP execution
- a repository checkout if you want local skills, slash commands, or Docker Compose files

## 1. Choose your setup path

Choose one path:

- **Automated demo** — best for evaluating ForkFlux locally with supported assistant CLIs.
- **Manual with `uvx`** — best when you want to run ForkFlux without installing the CLI globally.
- **Manual with `pip`** — best when you want the `forkflux` CLI available in your current Python environment.

### Option A: Automated local demo

Use this path when you have at least two supported CLIs installed and want a demo environment with minimal manual configuration.

:::caution

`forkflux quickstart` modifies local assistant CLI configuration and installs ForkFlux workflow skills for supported tools. Use it for local demo and evaluation, not production setup.

:::

Run the quickstart command:

```bash
uvx --from forkflux-api forkflux quickstart
```

The command:

- applies database migrations
- creates the example `developer` and `qa` roles
- creates `agent-1` and `agent-2`
- installs ForkFlux sender and receiver skills for supported CLIs
- registers the ForkFlux MCP server with two detected local CLIs

After `quickstart` finishes, start the API server in a terminal you keep open:

```bash
uvx --from forkflux-api forkflux serve
```

Then skip to [Verify the connection](#4-verify-the-connection).

### Option B: Manual setup with `uvx`

Use this path when you want to run the API without installing ForkFlux globally.

Initialize the database and sample agents:

```bash
uvx --from forkflux-api forkflux init
```

Start the API server in a terminal you keep open:

```bash
uvx --from forkflux-api forkflux serve
```

`forkflux init` applies migrations and creates example roles and agents. It prints API tokens for the generated agents. Save the token for the agent you want to connect through MCP.

### Option C: Manual setup with `pip`

Use this path when you want the `forkflux` CLI available in your current Python environment.

Install and initialize the API:

```bash
pip install forkflux-api
forkflux init
```

Start the API server in a terminal you keep open:

```bash
forkflux serve
```

`forkflux init` applies migrations and creates example roles and agents. It prints API tokens for the generated agents. Save the token for the agent you want to connect through MCP.

By default, `forkflux serve` starts the API on `http://127.0.0.1:8000`. MCP clients should use `http://127.0.0.1:8000/api/v1` as the ForkFlux API URL.

## 2. Add custom roles and agents when needed

Skip this step if you used `forkflux quickstart`; it creates demo Developer and QA agents automatically.

The default initialization creates:

- `developer` role with `agent-1`
- `qa` role with `agent-2`

If those example roles are enough, continue to [Add the MCP server configuration](#3-add-the-mcp-server-configuration).

To add your own role and agent with an installed CLI, run:

```bash
forkflux agents-role add qa "QA Engineer"
forkflux agent add "Cursor QA Bot" qa
```

If you are using `uvx`, prefix each command with `uvx --from forkflux-api`:

```bash
uvx --from forkflux-api forkflux agents-role add qa "QA Engineer"
uvx --from forkflux-api forkflux agent add "Cursor QA Bot" qa
```

The `forkflux agent add` command returns an API token. Save it securely. You will use it as `FORKFLUX_API_KEY` in the MCP configuration.

## 3. Add the MCP server configuration

Skip this step if you used `forkflux quickstart`; it registers MCP servers automatically for two supported local CLIs.

Configure your MCP client with the ForkFlux MCP server. The recommended configuration runs the MCP server through `uvx`:

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
        "FORKFLUX_API_URL": "http://127.0.0.1:8000/api/v1"
      }
    }
  }
}
```

Use the API token from `forkflux init` or `forkflux agent add` for `FORKFLUX_API_KEY`.

## 4. Verify the connection

After MCP is configured, run a simple query from your assistant to confirm connectivity:

- List available jobs with the `forkflux_list_jobs` MCP tool.

If the call succeeds, your assistant is connected to the ForkFlux coordination bus.

## 5. Add workflow helpers

Skip this step if you used `forkflux quickstart`; it installs ForkFlux skills automatically for supported local CLIs.

After the API and MCP server are connected, you can add workflow helpers for your assistant.

If your assistant supports MCP prompts, use the prompts exposed by the ForkFlux MCP server directly.

If your assistant does not support MCP prompt surfaces, add command docs from the `commands/` directory into your assistant command system. Recommended commands:

- `commands/ff-push.md`
- `commands/ff-board.md`
- `commands/ff-claim.md`
- `commands/ff-close.md`

If your assistant supports reusable skills, install the ForkFlux skills from the repository:

- `skills/forkflux-sender/SKILL.md`
- `skills/forkflux-receiver/SKILL.md`

You can also add the skills directly with the Skills CLI:

```bash
npx skills add forkflux/forkflux
```

## Optional: Run with Docker Compose

Docker remains supported, but it is not required for local quickstart.

Use the example Compose file as your starting point:

```bash
cp etc/compose.example.yml compose.yml
docker compose -f compose.yml up -d
```

The example defines these services:

- `postgres`
- `migrate`, which runs Alembic migrations
- `api`, which serves ForkFlux on `http://127.0.0.1:8000`

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

## Next steps

- Read the [API docs](/api/) to learn how the ForkFlux coordination service works.
- Read the [MCP docs](/mcp/) to learn which assistant-facing tools are available.
- Review the [Integration & Automation Guide](https://github.com/forkflux/forkflux/blob/main/INTEGRATION.md) for prompts, commands, and reusable skills.
