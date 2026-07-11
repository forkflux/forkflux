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

ForkFlux coordinates handoffs between human operators and their AI assistants through a shared coordination bus.

Before a handoff can happen:

1. The ForkFlux coordination bus is running.
2. Target roles, such as Developer, Frontend, QA, or Reviewer, are registered in the bus.
3. AI assistants are registered as agents with the roles they are allowed to perform.
4. The ForkFlux MCP server is installed in each assistant environment that needs to publish, inspect, claim, or close jobs.

A typical cross-device workflow looks like this:

1. **Alice starts the handoff** — Alice asks her AI assistant, such as Codex, to make changes and hand them to another role. For example: “Update the API contract and hand it off to Frontend.”
2. **The source assistant publishes a job** — the assistant loads the `forkflux-sender` skill and calls the ForkFlux MCP tool to create a job with the target role, context payload, constraints, priority, and artifacts.
3. **Bob checks the board** — Bob asks his AI assistant, such as Claude, to check for available jobs. For example: “Show me available ForkFlux jobs.”
4. **The target assistant lists jobs** — the assistant calls the ForkFlux MCP tool to fetch published jobs for its role and displays them as a readable table.
5. **Bob claims work** — Bob selects a job from the board. For example: “Claim the first job from the list.”
6. **The target assistant locks the job** — the assistant loads the `forkflux-receiver` skill and calls the ForkFlux MCP tool to claim the job atomically, moving it out of the shared pool so another assistant does not duplicate the work.
7. **Bob closes the job** — after the assistant finishes or cannot continue, Bob asks it to mark the job as `completed`, `failed`, or `cancelled` with the final result or failure reason.

## What is included

ForkFlux is a monorepo with two main packages:

| Package | Purpose |
|---|---|
| `forkflux-api` | Stateful FastAPI coordination service for agents, roles, jobs, events, artifacts, and lifecycle transitions. |
| `forkflux-mcp` | Model Context Protocol server that exposes ForkFlux tools and prompts to AI assistants. |

The MCP server exposes the core agent-facing tools:

| Tool | Purpose                                                               |
|---|-----------------------------------------------------------------------|
| `forkflux_create_job` | Publish a structured handoff job.                                     |
| `forkflux_list_jobs` | List jobs available in the shared task pool.                          |
| `forkflux_claim_job` | Atomically claim a published job and receive the full context payload. |
| `forkflux_claim_next_job` | Atomically claim the next available published job for a target role.   |
| `forkflux_change_job_status` | Close claimed work as `completed`, `failed`, or `cancelled`.          |
| `forkflux_job_details` | Receive the full context payload.                                     |

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

For complete setup instructions, see the [Quickstart](https://docs.forkflux.ai/quickstart).

## Documentation

Start with the [documentation](https://docs.forkflux.ai/) or jump directly to the page you need:

| Page | What you will find |
|---|---|
| [Overview](https://docs.forkflux.ai/) | What ForkFlux is, why agent handoffs need a coordination bus, and how the API and MCP server fit together. |
| [Quickstart](https://docs.forkflux.ai/quickstart) | Run ForkFlux locally, complete your first agent handoff, and use the zero-config demo path. |
| [Manual Setup](https://docs.forkflux.ai/manual-setup) | Initialize storage, create roles and agents, configure MCP, install skills, and run a handoff manually. |
| [Core Concepts](https://docs.forkflux.ai/core-concepts) | Agents, roles, jobs, task pools, lifecycle states, context payloads, constraints, and artifacts. |
| [Agent Workflows](https://docs.forkflux.ai/agent-workflows) | Standard sender and receiver workflows, lifecycle steps, workflow helpers, and human escalation points. |
| [CLI](https://docs.forkflux.ai/cli) | ForkFlux CLI commands, arguments, options, and examples. |
| [MCP Integration](https://docs.forkflux.ai/mcp-integration) | MCP server installation, client configuration, authentication, and available tools. |
| [Plugins](https://docs.forkflux.ai/plugins) | Install ForkFlux plugins that bring the MCP server, skills, and dashboard workflows into supported AI coding tools. |
| [Skills](https://docs.forkflux.ai/skills) | Available ForkFlux skills, installation options, and when to use skills instead of prompts or commands. |
| [Commands](https://docs.forkflux.ai/commands) | Slash command files, assistant compatibility, installation, and usage examples. |
| [MCP Prompts](https://docs.forkflux.ai/mcp-prompts) | Available MCP prompts and prompt-driven handoff workflows. |
| [API Reference](https://docs.forkflux.ai/api-reference) | Authentication, agents, jobs, roles, artifacts, events, schemas, and error responses. |
| [Self-Hosting](https://docs.forkflux.ai/self-hosting) | Docker setup, configuration, security guidance, and production-like deployment notes. |
| [FAQ](https://docs.forkflux.ai/faq) | Common questions about what ForkFlux is, what it is not, and how it differs from Jira. |
| [Contributing](https://docs.forkflux.ai/contributing) | How to report bugs, suggest features, make changes, and submit pull requests. |

## Community and contributing

Our goal is to make ForkFlux the standard job exchange protocol for AI-native engineering teams.

- 💬 Join Discord: [https://discord.gg/wTJVctJwn3](https://discord.gg/wTJVctJwn3)
- 🛠 Contribute: see the [Contributing guide](https://docs.forkflux.ai/contributing)
- 🐛 Report issues: [https://github.com/forkflux/forkflux/issues](https://github.com/forkflux/forkflux/issues)

## License

ForkFlux is licensed under Apache-2.0. See [LICENSE](LICENSE) for the full license text.
