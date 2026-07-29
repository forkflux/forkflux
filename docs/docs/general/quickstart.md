---
title: Quickstart
description: Run ForkFlux locally with zero-config setup and understand the automated demo path.
sidebar_position: 2
slug: /quickstart
---

# Getting Started

This guide gets a local ForkFlux collaboration and audit layer running and shows how two AI agents can complete a structured workflow handoff through the ForkFlux MCP server.

Use this page when you want the shortest path from zero to a working local demo. If you need full control over roles, agents, API tokens, MCP client configuration, or deployment settings, use the [Manual Setup](manual-setup.md) path.

## Quickstart

The fastest local path is the ForkFlux `quickstart` command. It creates a demo environment with example roles, agents, skills, and MCP server registrations for supported local assistant CLIs.

### Prerequisites

You need:

- Python 3.14+ for the ForkFlux API.
- `uvx` for the no-install package runner flow.
- An MCP-compatible assistant.
- At least two supported local assistant CLIs for the automated demo: Codex, Claude Code, OpenCode, or Hermes.

Optional tools:

- `pip` if you prefer installing the ForkFlux CLI into your current Python environment.
- Docker if you prefer containerized API execution.
- A repository checkout if you want to inspect local skills, slash commands, or Compose files.

### Run the automated demo setup

Run:

```bash
uvx --from forkflux forkflux quickstart
```

The command:

- applies database migrations
- creates the example `developer` and `qa` roles
- creates `agent-1` and `agent-2`
- installs ForkFlux sender and receiver skills for supported CLIs
- registers the ForkFlux MCP server with two detected local CLIs

By default, the MCP server, skills, and database are installed with `local` scope, meaning everything is private to the current working directory. Use the `--scope` option to change where MCP server registrations, workflow skills, and the SQLite database are stored:

```bash
# Install at user level (available across all projects)
uvx --from forkflux forkflux quickstart --scope user

# Install at project level (shared with repository collaborators)
uvx --from forkflux forkflux quickstart --scope project
```

Accepted values: `local` (default), `project`, `user`. When `user` is selected, skills are installed to the home directory (e.g. `~/.agents/skills`, `~/.claude/skills`) and MCP server config is stored at the user level. Database path resolution follows the same auto-detection logic as `serve` and `init`: the local path is checked first, then the global path. On a fresh install with no existing database, the database is created at the local path (`./.forkflux/forkflux.db`) regardless of scope.

:::note

Hermes does not support scoped skill installation. When Hermes is detected, skills are always installed to Hermes's default location regardless of the `--scope` value. The scope still applies to MCP server config and database path resolution for Hermes.

:::

:::caution

`forkflux quickstart` modifies local assistant CLI configuration and installs ForkFlux workflow helpers for supported tools. Use it for local demo and evaluation, not production setup.

:::

After `quickstart` finishes, start the API server in a terminal you keep open:

```bash
uvx --from forkflux forkflux serve
```

By default, the API runs on `http://127.0.0.1:8000`. MCP clients should use `http://127.0.0.1:8000/api/v1` as the ForkFlux API URL.

### Verify connectivity

Open an assistant that `quickstart` connected to ForkFlux and ask it to list available jobs. The assistant should call the `forkflux_list_jobs` MCP tool.

If the call succeeds, the assistant is connected to the ForkFlux collaboration bus. It is normal for the first board to be empty because no jobs have been published yet.

## Next steps

After `quickstart` finishes and the API is running, your agents are ready for handoffs. The demo setup creates two agents:

- `agent-1` with the `developer` role (sender)
- `agent-2` with the `qa` role (receiver)

To run your first handoff, see the [Workflow Helpers](workflow-helpers.md) page for guided sender and receiver workflows using skills, commands, or MCP prompts.

For a deeper understanding of the concepts behind ForkFlux, see [Core Concepts](core-concepts.md).
