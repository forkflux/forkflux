---
title: Agent Workflows
description: Understand the standard ForkFlux handoff flow between people, assistants, roles, and the shared coordination bus.
sidebar_position: 5
---

# Agent Workflows

ForkFlux coordinates handoffs between human operators and their AI assistants through a shared coordination bus.

## Overview

Before a handoff can happen:

1. The ForkFlux coordination bus is running.
2. Target roles, such as Developer, Frontend, QA, or Reviewer, are registered in the bus.
3. AI assistants are registered as agents with the roles they are allowed to perform.
4. The ForkFlux MCP server is installed in each assistant environment that needs to publish, inspect, claim, or close jobs.

A typical cross-device workflow looks like this:

1. **Alice starts the handoff** — Alice asks her AI assistant, such as Codex, to make changes and hand them to another role. For example: “Update the API contract and hand it off to Frontend.”
2. **The source assistant publishes a job** — the assistant loads the `forkflux-sender` skill and creates a job with the target role, context, constraints, priority, and artifacts.
3. **Bob checks the board** — Bob asks his AI assistant, such as Claude, to check for available jobs. For example: “Show me available ForkFlux jobs.”
4. **The target assistant lists jobs** — the assistant fetches published jobs for its role and displays them as a readable table.
5. **Bob claims work** — Bob selects a job from the board. For example: “Claim the first job from the list.”
6. **The target assistant locks the job** — the assistant loads the `forkflux-receiver` skill and claims the job atomically, so another assistant does not duplicate the work.
7. **Bob updates the job** — after the assistant finishes or cannot continue, Bob asks it to mark the job as `blocked`, `completed`, `failed`, or `cancelled` with the result, blocked reason, or failure reason.

## Lifecycle

Every handoff follows the same state flow:

1. **Publish** — a sender creates a job for a target role.
2. **List** — a receiver lists published jobs available to its role.
3. **Claim** — the receiver atomically claims one job.
4. **Execute** — the receiver completes the work using the packaged context.
5. **Update** — the receiver marks the job as `blocked`, `completed`, `failed`, or `cancelled`, or resumes blocked work as `in_progress`.

## Sender workflow

Use the sender workflow when work is ready for another role to continue, verify, review, document, or deploy.

The sender should include only what the next agent needs:

- the exact target role
- a short summary
- concrete acceptance criteria
- relevant files, decisions, logs, blockers, or instructions
- real artifact references, when useful
- an appropriate priority

After publishing, the sender should report the job ID and a concise summary:

```text
Published ForkFlux job 42 for qa.

Acceptance criteria:
- Health endpoint returns HTTP 200.
- Response body contains status: ok.
- Targeted health endpoint test passes.

Context included:
- Files touched: packages/api/forkflux_api/main.py, packages/api/tests/test_health.py
- Verification requested from QA.
```

Avoid dumping raw context payloads into chat unless the user asks for debugging details.

## Receiver workflow

Use the receiver workflow when an agent needs to pull work from the shared board.

The receiver should:

1. List available jobs for its role.
2. Show a readable board instead of raw JSON.
3. Claim only the selected job.
4. Read the full context before executing.
5. Complete the work locally.
6. Close the job with evidence or a clear failure reason.

Example board:

| Job ID | Priority | Summary | Created |
|---|---:|---|---|
| `42` | `30` | Verify health endpoint behavior | `2026-07-01T14:00:00Z` |

Example close response:

```text
Closed ForkFlux job 42 as completed.

Verification:
- Ran targeted health endpoint test.
- Confirmed HTTP 200 and expected response body.
```

If the receiver cannot complete the work, it should close the job as `failed` and include the blocker, attempted action, and relevant error excerpt.

## Workflow helpers

ForkFlux can guide assistants through the lifecycle in three ways:

| Helper | Best for | Learn more |
|---|---|---|
| MCP prompts | Assistants that expose MCP prompt surfaces. | [MCP Prompts](./mcp-prompts.md) |
| Skills | Assistants that support reusable skills or playbooks. | [Skills](./skills.md) |
| Commands | Assistants that support custom slash commands or command files. | [Commands](./commands.md) |

All helpers should call ForkFlux MCP tools directly. Agents should not use shell commands, `curl`, ad hoc scripts, mocked data, or direct API calls for workflow operations.

## When humans should step in

ForkFlux coordinates agents, but humans remain responsible for ambiguity and risk.

Ask a human before continuing when:

- the target role is unclear
- the job asks for production, destructive, or security-sensitive changes
- required files, services, or credentials are unavailable
- constraints conflict with the context or artifacts
- the receiver cannot meet the acceptance criteria
- the user asks the agent to override another agent's claim

When escalating, state the blocker, explain the risk, and list the exact decision needed.

Example:

```text
I need human confirmation before continuing.

Blocker: the job targets QA, but the payload asks me to deploy to production.
Risk: production deployment is outside the verified QA role and may be irreversible.
Required decision: confirm whether this job should be reassigned to an ops role or changed to QA-only verification.
```
