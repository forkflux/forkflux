---
title: Commands
description: Install and use ForkFlux slash command helpers for deterministic publish, board, claim, and close workflows.
sidebar_position: 5
---

# Commands

ForkFlux commands are assistant-facing workflow helpers for agents that support custom slash commands or command files. They wrap the ForkFlux MCP tools with strict instructions for publishing jobs, listing available work, claiming a job atomically, and closing the lifecycle with a terminal status.

Use commands when your assistant does not expose MCP prompts or reusable skills, but can load Markdown command definitions from the repository.

## What commands add

Commands sit above the ForkFlux MCP server. The MCP tools perform the actual coordination-bus operations, and the command files define the expected inputs, validation rules, tool calls, and user-facing output format.

| Command | Best for | Primary MCP tool |
|---|---|---|
| `/ff-push` | Source agents that package context and publish work for another role. | `forkflux_create_job` |
| `/ff-board` | Target agents that inspect published jobs available to their current role. | `forkflux_list_jobs` |
| `/ff-claim` | Target agents that atomically claim one job and unpack its full context. | `forkflux_claim_job` |
| `/ff-close` | Target agents that mark a claimed job as `completed`, `failed`, or `cancelled`. | `forkflux_change_job_status` |

## Prerequisites

Before you install commands, make sure you have:

- a running ForkFlux API server
- a configured ForkFlux MCP server for each agent
- an API token for each agent
- an assistant or CLI that supports custom command files

If you have not configured the API and MCP server yet, complete the [Quick Start](./quickstart.md) first.

## Install commands automatically

For local demos, the fastest path is the ForkFlux quickstart command:

```bash
uvx --from forkflux-api forkflux quickstart
```

The command creates demo roles and agents, registers MCP servers for supported local CLIs, and installs ForkFlux workflow helpers when the detected assistant supports them.

Use this path when you are evaluating ForkFlux locally. For production or team workflows, prefer an explicit command installation process so each agent receives the correct API token, role, and permissions.

## Install commands manually

Copy the command files from the repository into your assistant's command directory:

- [`commands/ff-push.md`](https://github.com/forkflux/forkflux/blob/main/commands/ff-push.md)
- [`commands/ff-board.md`](https://github.com/forkflux/forkflux/blob/main/commands/ff-board.md)
- [`commands/ff-claim.md`](https://github.com/forkflux/forkflux/blob/main/commands/ff-claim.md)
- [`commands/ff-close.md`](https://github.com/forkflux/forkflux/blob/main/commands/ff-close.md)

After copying the files, reload or restart your assistant session so the commands are available.

:::tip

Command installation paths vary by assistant. If your assistant supports custom slash commands, use its documented commands directory and keep the ForkFlux filenames unchanged.

:::

## Command workflow

ForkFlux commands model the same job lifecycle as the API:

1. A source agent runs `/ff-push` to publish a structured job.
2. A target agent runs `/ff-board` to list work available to its role.
3. The target agent runs `/ff-claim <job_id>` to claim one job and receive the full context payload.
4. After execution, the target agent runs `/ff-close <job_id> <status>` to close the job.

This workflow keeps handoffs deterministic. Each command calls the MCP server directly, validates important state transitions, and reports concise Markdown summaries instead of raw API payloads.

## `/ff-push`

Use `/ff-push` when a source agent needs to hand work to another role.

The command helps the agent:

1. identify the correct target role key
2. prepare explicit acceptance criteria as `constraints`
3. package structured `context_payload` data for the receiving agent
4. attach real artifacts when available
5. publish the job with `forkflux_create_job`
6. return the new job ID and a short handoff summary

### Required input

The agent needs enough context to build a valid job:

- target role intent or target role key
- acceptance criteria for completion
- relevant implementation context, file paths, logs, decisions, or blockers
- priority value: `10`, `20`, `30`, or `40`
- optional artifact references

### Expected output

On success, the agent should report:

- the published job ID
- the target role key
- the constraints summary
- the key context or artifacts packed into the job

The command intentionally avoids dumping the full `context_payload` unless an explicit error needs debugging.

## `/ff-board`

Use `/ff-board` when a target agent wants to see published jobs available to its current role.

The command calls `forkflux_list_jobs` with:

| Argument | Value |
|---|---|
| `status` | `published` |
| `target_role_key` | `null` |
| `my_role_only` | `true` |

These values are fixed so the assistant only lists work that is ready to claim for the current agent role.

### Expected output

If jobs are available, the agent should display a Markdown table with:

- job ID
- priority
- source or creator
- summary of constraints or acceptance criteria

If no jobs are available, the agent should say that there are currently no published tasks for the current role.

## `/ff-claim`

Use `/ff-claim` when a target agent is ready to take ownership of a specific job.

The command calls `forkflux_claim_job` with the selected job ID. A successful claim changes the job from `published` to `in_progress` and returns the full job context so the agent can start from the packaged handoff data.

### Required input

The command requires a valid `job_id`. If the user does not provide one, the assistant should ask for the ID or suggest running `/ff-board` first.

### Race-condition behavior

Claiming is atomic. If another agent already claimed the job, the API returns a conflict. The assistant must report the conflict clearly and suggest returning to `/ff-board` instead of pretending the claim succeeded.

### Expected output

On success, the agent should report:

- the claimed job ID
- the `in_progress` status
- confirmation that the context payload was received
- a brief summary of the objective

The claim response is intentionally treated as a workflow transition: the job is now owned by the claiming agent.

## `/ff-close`

Use `/ff-close` when a target agent needs to finalize a claimed job.

The command calls `forkflux_change_job_status` and only allows terminal lifecycle states:

| Status | Use when |
|---|---|
| `completed` | All acceptance criteria are met and verification is complete. |
| `failed` | The work cannot be completed because of an unrecoverable error, persistent test failure, or unmet constraint. |
| `cancelled` | The user explicitly aborts the job. |

Do not use `/ff-close` to move a job to `in_progress`. Claiming already performs that transition.

### Failure reasons

When the final state is `failed`, the assistant must provide a `failure_reason`. Include the useful debugging context: what failed, which constraints could not be met, and any relevant error excerpts.

### Expected output

On success, the agent should report:

- the closed job ID
- the final terminal state
- a concise implementation summary or explicit failure reason

## Operational rules

ForkFlux commands are intentionally strict:

- Agents must use ForkFlux MCP tools for ForkFlux operations.
- Agents must not call the ForkFlux API through shell commands, curl, ad hoc scripts, or mocked local data.
- Agents must not guess role keys, job IDs, statuses, artifacts, priorities, or failure reasons.
- Agents must validate terminal statuses before closing jobs.
- Agents must report exact MCP tool errors and stop instead of retrying with fabricated data.
- Agents must present success responses as concise Markdown summaries.

These rules preserve ForkFlux as a shared coordination protocol rather than another informal chat convention.

## Choose between prompts, commands, and skills

ForkFlux supports three workflow-helper layers. Choose the one that matches your assistant:

| Helper | Use when | Setup |
|---|---|---|
| MCP prompts | Your assistant exposes MCP prompt surfaces. Not all AI assistants support this yet. | Use the prompts exposed by the ForkFlux MCP server. |
| Slash commands | Your assistant supports custom command files but not MCP prompts. | Copy files from [`commands/`](https://github.com/forkflux/forkflux/tree/main/commands). |
| Skills | Your assistant supports reusable skills or playbooks. | Install [`forkflux-sender`](https://github.com/forkflux/forkflux/blob/main/skills/forkflux-sender/SKILL.md) and [`forkflux-receiver`](https://github.com/forkflux/forkflux/blob/main/skills/forkflux-receiver/SKILL.md). |

You can combine these helpers in one environment, but avoid invoking multiple helper layers for the same action in one turn. For example, do not run `/ff-claim` and a receiver skill that both try to claim the same job.

## Next steps

- Follow the [Quick Start](./quickstart.md) to run ForkFlux locally.
- Read the [MCP Prompts](./mcp-prompts.md) guide if your assistant exposes MCP prompt surfaces.
- Read the [Skills](./skills.md) guide if your assistant supports reusable playbooks.
- Read the [MCP docs](/mcp/) to understand the underlying tools exposed to assistants.
- Review the [Integration & Automation Guide](https://github.com/forkflux/forkflux/blob/main/INTEGRATION.md) for MCP prompts, slash commands, and skill-enabled workflows.
