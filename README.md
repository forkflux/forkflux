# ForkFlux 🐜

**Coordination bus for AI agents to hand off structured work across different machines, environments, and teammates without copy-pasting context, sharing temporary Markdown files, or using human task trackers as a data bus.**

📚 **Documentation:** [https://docs.forkflux.ai/](https://docs.forkflux.ai/)

> 🎥 **ForkFlux in action**

<p align="center">
  <img src="https://raw.githubusercontent.com/forkflux/forkflux/main/assets/demo.gif" width="100%" alt="ForkFlux Demo" />
</p>

## Why ForkFlux exists

AI agents can write code, run tests, and review changes, but they often work in isolated tools, machines, repositories, or accounts. When work needs to move from one agent to another, teams usually route context manually through chat, issue comments, or temporary files.

That creates fragile handoffs:

- context gets lost or duplicated
- receiving agents waste tokens reconstructing state
- acceptance criteria drift
- multiple agents can accidentally work on the same task
- final results and failure reasons are not captured consistently

ForkFlux replaces manual routing with a strict, machine-readable handoff protocol.

# What it is NOT

❌ NOT another AI assistant, extension, or LLM wrapper.

❌ NOT a local agent framework running on a single machine.

❌ NOT a shared memory for local AI assistants.

🔗 IT IS an infrastructure-grade data stream to pass clean context from a developer's local AI agent to another engineer's AI agent on another device.

## How it works

ForkFlux uses a shared job pool with explicit lifecycle transitions:

1. **Publish** — a source agent creates a job with a target role, priority, constraints, context payload, and artifacts.
2. **Claim** — a target agent lists available work for its role and atomically claims one job.
3. **Execute** — the target agent works from the packaged context instead of reconstructing it from chat.
4. **Close** — the target agent marks the job as `completed`, `failed`, or `cancelled` with a result summary or failure reason.

## What is included

ForkFlux is a monorepo with two main packages:

| Package | Purpose |
|---|---|
| `forkflux-api` | Stateful FastAPI coordination service for agents, roles, jobs, events, artifacts, and lifecycle transitions. |
| `forkflux-mcp` | Model Context Protocol server that exposes ForkFlux tools and prompts to AI assistants. |

The MCP server exposes the core agent-facing tools:

| Tool | Purpose |
|---|---|
| `forkflux_create_job` | Publish a structured handoff job. |
| `forkflux_list_jobs` | List jobs available in the shared task pool. |
| `forkflux_claim_job` | Atomically claim a published job and receive the full context payload. |
| `forkflux_change_job_status` | Close claimed work as `completed`, `failed`, or `cancelled`. |

ForkFlux also includes workflow helpers for prompt-aware assistants, slash command systems, and reusable skills.

## Quick start

Run the local demo setup:

```bash
uvx --from forkflux-api forkflux quickstart
```

Start the API server:

```bash
uvx --from forkflux-api forkflux serve
```

The quickstart flow creates example Developer and QA agents, installs supported workflow helpers, and registers the MCP server with supported local assistant CLIs.

For complete setup instructions, see the [Getting Started guide](https://docs.forkflux.ai/getting-started).

## Documentation

- [Overview](https://docs.forkflux.ai/) — what ForkFlux is and why the coordination bus model matters.
- [Getting Started](https://docs.forkflux.ai/getting-started) — quickstart, first handoff, and zero-config setup.
- [Core Concepts](https://docs.forkflux.ai/core-concepts) — agents, roles, jobs, lifecycle states, context, and artifacts.
- [Agent Workflows](https://docs.forkflux.ai/agent-workflows) — sender and receiver workflows, MCP prompts, skills, commands, and escalation.
- [MCP Integration](https://docs.forkflux.ai/mcp-integration) — client configuration, authentication, tool workflow, and tool reference.
- [API Reference](https://docs.forkflux.ai/api-reference) — endpoints, schemas, artifacts, events, and errors.
- [Guides](https://docs.forkflux.ai/guides) — cross-device handoff, multi-repo handoff, long-running tasks, and context patterns.
- [Self-Hosting](https://docs.forkflux.ai/self-hosting) — Docker setup, configuration, security, and production checklist.
- [Troubleshooting](https://docs.forkflux.ai/troubleshooting) — connection, authentication, validation, claim, and Docker issues.
- [Contributing](https://docs.forkflux.ai/contributing) — development setup, tests, commits, and pull requests.
- [FAQ](https://docs.forkflux.ai/faq) — what ForkFlux is not and how it differs from Jira.

## Community and contributing

Our goal is to make ForkFlux the standard job exchange protocol for AI-native engineering teams.

- 💬 Join Discord: [https://discord.gg/wTJVctJwn3](https://discord.gg/wTJVctJwn3)
- 🛠 Contribute: see the [Contributing guide](https://docs.forkflux.ai/contributing)
- 🐛 Report issues: [https://github.com/forkflux/forkflux/issues](https://github.com/forkflux/forkflux/issues)

## License

ForkFlux is licensed under Apache-2.0. See [LICENSE](LICENSE) for the full license text.
