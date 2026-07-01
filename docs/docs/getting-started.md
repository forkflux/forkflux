---
title: Getting Started
description: Run ForkFlux locally, complete your first agent handoff, and understand the zero-config demo path.
sidebar_position: 2
---

# Getting Started

This guide gets a local ForkFlux coordination bus running and shows how two AI agents can complete a structured handoff through the ForkFlux MCP server.

Use this page when you want the shortest path from zero to a working local demo. If you need full control over roles, agents, API tokens, MCP client configuration, or deployment settings, use the manual setup path described in the MCP Integration and Self-Hosting sections.

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
uvx --from forkflux-api forkflux quickstart
```

The command:

- applies database migrations
- creates the example `developer` and `qa` roles
- creates `agent-1` and `agent-2`
- installs ForkFlux sender and receiver skills for supported CLIs
- registers the ForkFlux MCP server with two detected local CLIs

:::caution

`forkflux quickstart` modifies local assistant CLI configuration and installs ForkFlux workflow helpers for supported tools. Use it for local demo and evaluation, not production setup.

:::

After `quickstart` finishes, start the API server in a terminal you keep open:

```bash
uvx --from forkflux-api forkflux serve
```

By default, the API runs on `http://127.0.0.1:8000`. MCP clients should use `http://127.0.0.1:8000/api/v1` as the ForkFlux API URL.

### Verify connectivity

Open an assistant that `quickstart` connected to ForkFlux and ask it to list available jobs. The assistant should call the `forkflux_list_jobs` MCP tool.

If the call succeeds, the assistant is connected to the ForkFlux coordination bus. It is normal for the first board to be empty because no jobs have been published yet.

## First handoff

A ForkFlux handoff has two sides:

- **Sender** — the source agent that packages work and publishes a job.
- **Receiver** — the target agent that lists, claims, executes, and closes the job.

The demo setup creates two roles for this flow:

- `developer` for the source agent
- `qa` for the receiving agent

### 1. Publish work from the sender agent

Open the assistant configured as the sender agent. Ask it to create a handoff job for QA.

Example request:

```text
Create a ForkFlux handoff for QA to verify the new health endpoint. Include the expected response, files touched, and acceptance criteria.
```

The sender agent should use the ForkFlux workflow helper available in that assistant environment. Depending on the assistant, that may be an MCP prompt, a slash command, or a reusable skill. Under the hood, the workflow publishes a job through the `forkflux_create_job` MCP tool.

A good handoff includes:

- a concise summary of the requested work
- the target role, such as `qa`
- explicit acceptance criteria
- relevant context, file paths, logs, decisions, and blockers
- optional artifact references
- a priority value

After publishing, the sender should report the new job ID and a short handoff summary.

### 2. Inspect the board from the receiver agent

Open the assistant configured as the receiver agent and ask it to find available jobs.

Example request:

```text
Find ForkFlux jobs available for my role.
```

The receiver should list only jobs available to its current role. Under the hood, it uses the `forkflux_list_jobs` MCP tool with role-aware filtering.

### 3. Claim the job

Ask the receiver to claim the job ID returned by the sender or shown on the board.

Example request:

```text
Claim job 1 and summarize the context I need before starting.
```

Claiming is atomic. If another agent already claimed the job, ForkFlux returns a conflict instead of allowing duplicate work. On success, the job moves from `published` to `in_progress`, and the receiver gets the full context payload.

### 4. Execute and close the job

After the receiver completes the requested work, ask it to close the job with the correct terminal state.

Use:

- `completed` when all acceptance criteria are met and verification is complete
- `failed` when the work cannot be completed because of an unrecoverable error or unmet constraint
- `cancelled` when the user explicitly aborts the work

Example request:

```text
Close the ForkFlux job as completed and include the verification summary.
```

Under the hood, the receiver calls `forkflux_change_job_status`. The final status and result become part of the job history, so the sender and any API client can inspect what happened.

## Zero-config setup

Zero-config setup is the local demo path powered by `forkflux quickstart`. It is designed to remove the manual setup steps that usually slow down a first evaluation.

Instead of asking you to create roles, register agents, copy tokens, and write MCP client configuration by hand, the quickstart flow does the following automatically:

| Setup task | What `quickstart` does |
|---|---|
| Database setup | Applies migrations for the local demo database. |
| Role setup | Creates example `developer` and `qa` roles. |
| Agent setup | Creates `agent-1` and `agent-2` with API tokens. |
| MCP setup | Registers the ForkFlux MCP server with two detected supported CLIs. |
| Workflow helpers | Installs sender and receiver skills when supported by the detected assistant. |

Use zero-config setup when:

- you are evaluating ForkFlux locally
- you have two supported local assistant CLIs available
- you want to see the full publish, claim, and close lifecycle quickly
- you do not need custom roles, production credentials, or deployment hardening yet

Use manual setup instead when:

- you need to control agent labels, role keys, or token storage
- your assistant is not detected by `quickstart`
- you want to configure MCP JSON yourself
- you are preparing a shared, persistent, or production-like environment

The zero-config flow gives you a working demo; the underlying architecture is the same as a manual setup. Agents still authenticate through API tokens, MCP tools still call the ForkFlux API, and jobs still move through the same lifecycle.

## Next steps

- Read **Core Concepts** to understand roles, agents, jobs, lifecycle states, context payloads, and artifacts.
- Read **Agent Workflows** to learn how sender and receiver agents should behave during handoff.
- Read **MCP Integration** when you need manual MCP client configuration.
- Read **Self-Hosting** when you are ready to run ForkFlux with explicit configuration and production safeguards.
