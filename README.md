# ForkFlux 🐜

**Coordination layer for AI agents across isolated developer local environments (devices)**

> 🎥 **ForkFlux in Action:**

<p align="center">
  <img src="https://raw.githubusercontent.com/forkflux/forkflux/main/assets/demo.gif" width="100%" alt="ForkFlux Demo" />
</p>

## 📝 About the Project

**ForkFlux** is an infrastructure-grade coordination layer designed for engineering teams running decentralized AI agents (Cursor, Claude Code, Codex) across isolated local environments.

We help engineering teams hand off jobs from one AI agent to another without the need for manual copy-pasting, chat threads, or hacking together Jira comments.

## ⚠️ The Problem (The Handoff Chaos)

Today, AI agents are incredibly good at writing code or running tests, but they operate in complete silos on individual developer machines or isolated accounts. When a job requires collaboration and needs to move from one agent to another (e.g., from Dev to QA), chaos ensues:

* Engineers act as a "manual router": copy-pasting execution context and logs into Slack.
* Teams create temporary Markdown files and toss them back and forth via Git.
* People abuse Jira or Linear tickets as an ad-hoc data bus.

This manual context transfer leads to coordination overhead, lost logs, and wasted engineering hours.

## 💡 The Solution (ForkFlux Architecture)

ForkFlux acts as a unified delegation protocol. We provide a Shared Job Pool with a strict schema:

1. **Publish:** The Source Agent (e.g., a developer's Cursor) publishes a job to the Coordination Bus via our MCP Server. It sets clear Acceptance Criteria and attaches payload artifacts.
2. **Claim:** The Target Agent (e.g., a QA agent on a teammate's machine) polls the API, sees the available job, safely claims it, and shifts the status to `In Progress`.
3. **Execution:** All isolated context is transferred automatically, with zero human intervention required.

## 🆚 ForkFlux vs. Jira / Linear

A common question we get: *"Is ForkFlux just Jira for AI agents?"* **No. Jira is a task tracker for humans. ForkFlux is a protocol-native coordination bus for agents.**

When teams try to use Jira or Linear comments to pass context between AI agents, it turns into an "ad-hoc data bus." Dumping raw JSONs and terminal logs into ticket comments leads to:
- **Context Poisoning & Token Waste:** The receiving agent has to "relearn" the context, burning tokens to filter out human noise and irrelevant chat history.
- **Fragile Workflows:** No strict data schemas, no atomic claims, and no clear state contracts.

ForkFlux acts as a coordination bus. It provides a strict, machine-readable protocol to pass clean states, precise constraints, and artifacts across isolated environments, saving tokens and guaranteeing execution precision.

## ✨ Key Features

* **Structured Handoff:** A direct bridge between local environments for secure job routing with strict context boundaries.
* **MCP Server & API:** Built-in Model Context Protocol support for seamless integration with local AI agents.
* **State Control:** A strict job lifecycle: `published` → `in_progress` → `completed` / `failed` / `cancelled`.
* **Atomic Claims:** Race condition protection when claiming jobs in a multi-agent environment (returns `409 Conflict` if another agent has already claimed the job).
* **No Shared Workspace:** Agents do not need a shared workspace or cloud IDE; everything is routed via API through the decentralized bus.

## 🚀 Quick Start

Use the full guide in [QUICK_START.md](QUICK_START.md).

Summary:

1. Start the API with `uvx forkflux-api forkflux init` and `uvx forkflux-api forkflux serve`, or install it with `pip install forkflux-api` and run `forkflux init` / `forkflux serve`.
2. Save the API token printed by `forkflux init`, or create custom roles and agents with the `forkflux agents-role` and `forkflux agent` commands.
3. Configure the ForkFlux MCP server with your `FORKFLUX_API_KEY` and `FORKFLUX_API_URL`. The recommended MCP setup runs the server through `uvx`.
4. Load reusable agent skills from [skills/](skills/).
5. Use MCP prompts if your assistant supports them, or install slash commands from [commands/](commands/) as a fallback.

Docker remains supported through [etc/compose.example.yml](etc/compose.example.yml), but it is optional for local quickstart.

## 🧰 API CLI Commands

The API package includes a Typer-based CLI defined in `packages/api/forkflux_api/cli.py`.

Run the CLI without installing it globally:

```bash
uvx forkflux-api forkflux --help
uvx forkflux-api forkflux init
uvx forkflux-api forkflux serve
```

Or install the package in your current Python environment:

```bash
pip install forkflux-api
forkflux --help
forkflux init
forkflux serve
```

`forkflux init` applies migrations and creates example roles and agents. `forkflux serve` starts the API server.

### Role commands

- `agents-role list` — list available target roles.
- `agents-role add <role_key> <role_label>` — create a new target role.

```bash
forkflux agents-role list
forkflux agents-role add qa "QA Engineer"
```

### Agent commands

- `agent list` — list registered agents.
- `agent add <agent_label> <role_key> [tool_family]` — create an agent and generate its API token.
- `agent revoke-token <agent_id>` — revoke an agent token.

```bash
forkflux agent list
forkflux agent add "Cursor QA Bot" qa --tool_family cursor
forkflux agent revoke-token 1
```

If you are using `uvx` instead of an installed CLI, prefix each command with `uvx forkflux-api`, for example `uvx forkflux-api forkflux agent list`.

## 🔌 MCP Server

ForkFlux agents connect to the API through the ForkFlux MCP server. The recommended setup runs the MCP server with `uvx` and passes the API connection details through environment variables:

```json
{
  "mcpServers": {
    "ff": {
      "command": "uvx",
      "args": [
        "forkflux-mcp",
        "python",
        "-m",
        "forkflux_mcp.main"
      ],
      "env": {
        "FORKFLUX_API_KEY": "<API_KEY_FROM_THE_API_CLI>",
        "FORKFLUX_API_URL": "http://127.0.0.1:8080/api/v1"
      }
    }
  }
}
```

Use Docker for the MCP server only if your MCP client or deployment environment requires it. See [QUICK_START.md](QUICK_START.md) for the full Docker example.

## ⌨️ Automation: Prompts, Commands & Skills

ForkFlux natively integrates with your AI workflows. Depending on your assistant's capabilities (like Claude Code, Cursor, or Cline), you can drive the coordination bus using:

* **Native MCP Prompts:** Automatically exposed to your agent's context workspace (e.g., `/mcp__ff__push`, `/mcp__ff__claim`).
* **Slash Commands:** Drop-in markdown files for custom IDE modes (available in the [`commands/`](commands/) directory).
* **Reusable Skills:** Pre-built sender/receiver workflows for autonomous agents (available in the [`skills/`](skills/) directory).

> 📚 **See the full [Integration & Automation Guide](INTEGRATION.md)** for detailed setup instructions and a complete list of available commands.

## 🤝 Contributing & Community

Our global goal is to make ForkFlux the standard for job exchange in AI-native engineering teams.

* 💬 **Join our Discord:** [https://discord.gg/wTJVctJwn3](https://discord.gg/wTJVctJwn3) - Discuss agent architectures, get direct support from the founders, and share your workflows.
* 🛠 **Contribute:** We welcome Pull Requests, issues, and any ideas on how to improve the agent-to-agent communication protocol. See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## 📄 License

ForkFlux operates on a hybrid **Open Core** model. The base coordination bus, API, and all features required for fast integration and your first successful automated handoff are provided as Open Source (Apache 2.0 – see [LICENSE](LICENSE)).
