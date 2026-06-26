---
title: Skills
description: Install and use ForkFlux reusable skills for deterministic sender and receiver agent workflows.
---

# Skills

ForkFlux skills are reusable agent playbooks that keep handoff behavior consistent across skill-enabled assistants. They guide source agents through publishing work and target agents through listing, claiming, executing, and closing jobs through the ForkFlux MCP tools.

Use skills when you want repeatable workflows across agents without rewriting instructions in every chat session.

## What skills add

Skills sit above the ForkFlux MCP tools. The MCP server provides the actual operations, and the skills define when to call them, how to validate inputs, and how to present results to the user.

| Skill | Best for | Primary MCP tools |
|---|---|---|
| [`forkflux-sender`](https://github.com/forkflux/forkflux/skills/forkflux-sender/SKILL.md) | Source agents that package context and publish handoff jobs. | `forkflux_create_job`, `forkflux_change_job_status` |
| [`forkflux-receiver`](https://github.com/forkflux/forkflux/skills/forkflux-receiver/SKILL.md) | Target agents that discover, claim, execute, and close jobs. | `forkflux_list_jobs`, `forkflux_claim_job`, `forkflux_change_job_status` |

## Prerequisites

Before you install skills, make sure you have:

- a running ForkFlux API server
- a configured ForkFlux MCP server for each agent
- an API token for each agent
- an assistant or CLI that supports reusable skills

If you have not configured the API and MCP server yet, complete the [Quick Start](./quickstart.md) first.

## Install skills automatically

For local demos, the fastest path is the ForkFlux quickstart command:

```bash
uvx --from forkflux-api forkflux quickstart
```

The command creates demo roles and agents, registers MCP servers for supported local CLIs, and installs the ForkFlux sender and receiver skills when the detected assistant supports them.

Use this path when you are evaluating ForkFlux locally. For production or team workflows, prefer an explicit MCP and skill installation process so each agent receives the correct API token, role, and permissions.

## Install skills manually

If your assistant supports the Skills CLI, install the ForkFlux skill bundle directly:

```bash
npx skills add forkflux/forkflux
```

You can also install or copy the skill files from the repository:

- [`skills/forkflux-sender/SKILL.md`](https://github.com/forkflux/forkflux/skills/forkflux-sender/SKILL.md)
- [`skills/forkflux-receiver/SKILL.md`](https://github.com/forkflux/forkflux/skills/forkflux-receiver/SKILL.md)

After installation, reload or restart your assistant session so the new skills are available in context.

## Sender skill

Use [`forkflux-sender`](https://github.com/forkflux/forkflux/skills/forkflux-sender/SKILL.md) when a source agent needs to hand work to another role.

The sender skill helps the agent:

1. confirm that a handoff is actually needed
2. select a valid target role instead of guessing one
3. prepare acceptance criteria as explicit constraints
4. package structured context, file paths, logs, and implementation notes
5. publish the job with `forkflux_create_job`
6. return a concise human-readable summary instead of raw API JSON

### When to use it

Use the sender skill when:

- you explicitly ask an agent to hand off work
- an implementation is complete and ready for review, QA, documentation, deployment, or another specialized role
- another isolated assistant needs enough structured context to continue without reconstructing the task from chat history

Do not use it for normal intermediate coding iterations or incomplete debugging loops.

### Expected output

On success, the source agent should summarize:

- the published job ID
- the selected target role
- the acceptance criteria summary
- the context and artifacts packed into the job

The skill intentionally avoids dumping the raw `context_payload` into chat.

## Receiver skill

Use [`forkflux-receiver`](https://github.com/forkflux/forkflux/skills/forkflux-receiver/SKILL.md) when a target agent needs to pick up work from the coordination bus.

The receiver skill helps the agent:

1. list only published jobs available to the current agent role
2. display a readable board of available work
3. wait for confirmation before claiming a job
4. atomically claim the selected job with `forkflux_claim_job`
5. unpack the full context payload and acceptance criteria
6. execute locally
7. close the job with `completed`, `failed`, or `cancelled`

### When to use it

Use the receiver skill when:

- an agent is ready to inspect available work for its role
- a user asks the agent to claim a ForkFlux task
- a claimed job needs to be closed with a terminal status

### Expected output

During the board flow, the target agent should show a Markdown table with job ID, priority, source or creator, summary, and created time.

After claiming a job, the agent should confirm the job is `in_progress`, summarize the objective, and ask before starting execution.

When closing a job, the agent should report the final terminal state and a short implementation summary or failure reason.

## Choose between prompts, commands, and skills

ForkFlux supports three workflow-helper layers. Choose the one that matches your assistant:

| Helper | Use when | Setup |
|---|---|---|
| MCP prompts | Your assistant exposes MCP prompt surfaces. | No extra setup beyond the ForkFlux MCP server. |
| Slash commands | Your assistant supports custom command files but not MCP prompts. | Copy files from [`commands/`](https://github.com/forkflux/forkflux/commands/). |
| Skills | Your assistant supports reusable skills or playbooks. | Install [`forkflux-sender`](https://github.com/forkflux/forkflux/skills/forkflux-sender/SKILL.md) and [`forkflux-receiver`](https://github.com/forkflux/forkflux/skills/forkflux-receiver/SKILL.md). |

You can combine these helpers, but avoid invoking multiple helper layers for the same action in one turn. For example, do not run a slash command and a skill that both try to claim the same job.

## Operational rules

ForkFlux skills are intentionally strict:

- Agents must use the ForkFlux MCP tools for ForkFlux operations.
- Agents must not call the ForkFlux API through shell commands, curl, ad hoc scripts, or mocked local data.
- Agents must not guess role keys, job IDs, artifacts, statuses, or failure reasons.
- Agents must present success responses as concise Markdown summaries.
- Agents must report exact tool errors and stop instead of retrying with fabricated data.

These rules preserve ForkFlux as a shared coordination protocol rather than another informal chat convention.

## Next steps

- Follow the [Quick Start](./quickstart.md) to run ForkFlux locally.
- Read the [MCP docs](/mcp/) to understand the underlying tools exposed to assistants.
- Review the [Integration & Automation Guide](https://github.com/forkflux/forkflux/blob/main/INTEGRATION.md) for MCP prompts, slash commands, and skill-enabled workflows.
