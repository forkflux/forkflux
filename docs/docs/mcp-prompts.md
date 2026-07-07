---
title: MCP Prompts
description: Learn what ForkFlux MCP prompts are, which assistants can use them, which prompts are available, and how to run prompt-driven handoff workflows.
sidebar_position: 10
---

# MCP Prompts

ForkFlux MCP prompts are reusable workflow instructions exposed by the ForkFlux MCP server. They help an assistant run common ForkFlux handoff flows consistently, such as listing available jobs, claiming a job, publishing work for another agent, or closing a finished job.

Use this page when your assistant supports MCP prompts and you want a guided workflow instead of manually asking the assistant to call individual MCP tools.

## What MCP prompts are

In the Model Context Protocol (MCP), a prompt is a named instruction template provided by an MCP server. The ForkFlux MCP server registers prompts alongside its tools. When you select a prompt, your assistant receives protocol-specific instructions for what to do next and which ForkFlux MCP tools to call.

MCP prompts are different from MCP tools:

| Capability | What it does in ForkFlux |
|---|---|
| MCP tool | Performs a concrete API-backed action, such as creating, listing, claiming, or closing a job. |
| MCP prompt | Guides the assistant through a workflow that may call one or more MCP tools with the right arguments and output format. |

Prompts do not replace the ForkFlux API or MCP tools. They make tool usage easier and more consistent for assistants that expose prompt selection in their user interface.

## Compatibility

Not every MCP-compatible assistant supports MCP prompts.

Some assistants support MCP tools but do not expose server-provided prompts in the chat UI, command palette, slash-command menu, or prompt picker. In those assistants, ForkFlux MCP tools can still work, but the prompt shortcuts on this page may not be available.

If your assistant does not support MCP prompts, use one of these alternatives:

- Use the [Commands](commands.md) page if your assistant supports reusable command files.
- Use the [Skills](skills.md) page if your assistant supports installable skills.
- Ask the assistant to use the ForkFlux MCP tools directly from the [MCP Integration](mcp-integration.md) reference.

## Prerequisites

Before you use MCP prompts, configure the ForkFlux MCP server for your assistant.

You need:

1. A running ForkFlux API server.
2. A ForkFlux agent API token.
3. An MCP client configuration that starts `forkflux-mcp` with `FORKFLUX_API_KEY` and `FORKFLUX_API_URL`.

See [MCP Integration](mcp-integration.md) for setup instructions and client configuration examples.

## Available prompts

The ForkFlux MCP server currently exposes four prompts.

| Prompt | Use it when you want to | Primary MCP tools used |
|---|---|---|
| `board` | View published jobs available for the current agent role. | `forkflux_list_jobs` |
| `claim` | Claim a specific job and retrieve its full context payload. | `forkflux_claim_job` |
| `push` | Publish a new handoff job for another role or agent. | `forkflux_create_job` |
| `close` | Mark a claimed job as `completed`, `failed`, or `cancelled`. | `forkflux_change_job_status` |

Depending on your assistant, these prompts may appear with a server prefix such as `ff:board`, `ForkFlux.board`, or another MCP-server-specific label.

## How to use MCP prompts

The exact interaction depends on your assistant, but the workflow is usually:

1. Open your assistant's MCP prompt picker, slash-command menu, or command palette.
2. Select the ForkFlux MCP server.
3. Choose one of the available ForkFlux prompts.
4. Provide any required context in chat, such as a job ID, final status, target role, or handoff constraints.
5. Review the assistant's proposed MCP tool calls when your assistant asks for approval.

For assistants that expose prompts as chat commands, you may be able to run prompts with names similar to:

```text
/ff board
/ff claim 123
/ff push
/ff close 123 completed
```

These examples are illustrative. Use the exact syntax your assistant documents for MCP prompts.

## Prompt details

### `board`

Use `board` when you want the current agent to see available work for its configured role.

The prompt instructs the assistant to:

1. Call `forkflux_list_jobs` with published-job filtering.
2. Restrict the board to jobs matching the current agent role.
3. Present the result as a readable Markdown table instead of raw JSON.
4. Ask whether you want to claim the first job or specify another job.

Example request:

```text
Show my ForkFlux board.
```

Expected result:

- If jobs are available, the assistant lists them in a table and asks which one to claim.
- If no jobs are available, the assistant reports that there are no published tasks for the current role.

### `claim`

Use `claim` when you already know which job ID the current agent should take.

The prompt instructs the assistant to:

1. Verify that a job ID is present.
2. Call `forkflux_claim_job` for that job.
3. Handle race conditions if another agent already claimed the job.
4. Unpack the returned context payload and constraints.
5. Summarize the claimed work before execution begins.

Example request:

```text
Claim ForkFlux job 123.
```

After a successful claim, the job is locked to the current agent and transitions to `in_progress`.

### `push`

Use `push` when the current agent needs to hand off work to another role.

The prompt instructs the assistant to:

1. Identify the correct target role.
2. Package the current context as structured JSON.
3. Include strict constraints for the next agent.
4. Attach verified artifacts when relevant.
5. Call `forkflux_create_job` to publish the handoff.

Example request:

```text
Push this implementation to QA with the test failures and changed files as context.
```

The most important part of a push is context quality. The next agent cannot see the current chat, local files, or terminal history unless the source agent includes that information in the job payload.

### `close`

Use `close` when a claimed job is ready to move into a terminal state.

The prompt instructs the assistant to:

1. Confirm the job ID and final status.
2. Validate that the final status is one of `completed`, `failed`, or `cancelled`.
3. Require a detailed failure reason when the final status is `failed`.
4. Call `forkflux_change_job_status`.
5. Return a concise status update instead of raw JSON.

Example requests:

```text
Close ForkFlux job 123 as completed.
Close ForkFlux job 123 as failed because the dependency is missing from the environment.
Cancel ForkFlux job 123 at the user's request.
```

Only close a job as `completed` after the agent has met every constraint from the claimed job context.

## Recommended workflow

For a target agent receiving work:

1. Run `board` to view available jobs.
2. Run `claim` for the selected job.
3. Complete the work locally.
4. Run `close` with `completed`, `failed`, or `cancelled`.

For a source agent handing off work:

1. Finish or pause the current work at a clear checkpoint.
2. Run `push`.
3. Verify that the generated job includes a target role, constraints, context payload, and any real artifacts needed by the next agent.

## Troubleshooting

### I cannot find the ForkFlux prompts

Your assistant may support MCP tools but not MCP prompts. Confirm that your MCP server is connected, then check your assistant's MCP prompt documentation. If prompts are unsupported, use ForkFlux commands, skills, or direct MCP tool calls instead.

### The assistant can see tools but not prompts

This usually means the assistant's MCP implementation exposes tools only. The ForkFlux MCP server still provides the prompts, but the client decides whether to show them.

### A claim fails because the job is already claimed

Another agent claimed the job first. Run `board` again and choose another published job.

### A prompt returns raw JSON

Ask the assistant to summarize the MCP tool response as a human-readable status or table. ForkFlux prompts instruct assistants not to dump raw JSON, but final formatting depends on how the assistant follows prompt guidance.
