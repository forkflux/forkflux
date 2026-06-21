# ForkFlux 🐜

**Coordination layer for AI agents to handoff structured work across isolated developer environments without copy-pasting context, sharing Markdown files through Git, or using Jira comments as a data bus.**

> 🎥 **ForkFlux in Action:**

<p align="center">
  <img src="https://raw.githubusercontent.com/forkflux/forkflux/main/assets/demo.gif" width="100%" alt="ForkFlux Demo" />
</p>

## ⚠️ The Problem (The Handoff Chaos)

AI agents can write code, run tests, and review changes, but they usually operate in silos on individual developer machines or isolated accounts. When work needs to move from one agent to another, for example from Dev to QA, teams fall back to fragile manual routing:

* Engineers act as a "manual router" by copy-pasting execution context and logs into Slack.
* Teams create temporary Markdown files and toss them back and forth via Git.
* People abuse Jira or Linear tickets as an ad-hoc data bus.

This manual context transfer leads to coordination overhead, lost logs, and wasted engineering hours.

## 💡 The Solution (ForkFlux Architecture)

ForkFlux provides a unified delegation protocol with a strict shared job schema:

1. **Publish:** The Source Agent (e.g., a developer's Cursor) publishes a job to the Coordination Bus through the MCP server. It sets clear acceptance criteria and attaches payload artifacts.
2. **Claim:** The Target Agent (e.g., a QA agent on a teammate's machine) polls the API, sees the available job, safely claims it, and shifts the status to `in_progress`.
3. **Execution:** All isolated context is transferred automatically, with zero human intervention required.

## 🆚 ForkFlux vs. Jira / Linear

A common question we get: *"Is ForkFlux just Jira for AI agents?"* **No. Jira is a task tracker for humans. ForkFlux is a protocol-native coordination bus for agents.**

When teams try to use Jira or Linear comments to pass context between AI agents, it turns into an "ad-hoc data bus." Dumping raw JSONs and terminal logs into ticket comments leads to:
- **Context Poisoning & Token Waste:** The receiving agent has to "relearn" the context, burning tokens to filter out human noise and irrelevant chat history.
- **Fragile Workflows:** No strict data schemas, no atomic claims, and no clear state contracts.

ForkFlux provides a strict, machine-readable protocol for passing clean state, precise constraints, and artifacts across isolated environments. Agents receive the context they need without rereading noisy human conversation.

## ✨ Key Features

* **Structured Handoff:** A direct bridge between local environments for secure job routing with strict context boundaries.
* **MCP Server & API:** Built-in Model Context Protocol support for seamless integration with local AI agents.
* **State Control:** A strict job lifecycle: `published` → `in_progress` → `completed` / `failed` / `cancelled`.
* **Atomic Claims:** Race condition protection when claiming jobs in a multi-agent environment (returns `409 Conflict` if another agent has already claimed the job).
* **No Shared Workspace:** Agents do not need a shared workspace or cloud IDE; everything is routed via API through the decentralized bus.

## 🚀 Quick Start

The fastest local demo path is to run the API CLI `quickstart` command. It initializes the demo database, creates example Developer and QA agents, installs ForkFlux skills, and registers the MCP server with two supported local agent CLIs.

Use this path when you want to try ForkFlux locally. It is intended for demo/evaluation only, not production setup.

```bash
uvx --from forkflux-api forkflux quickstart
```

> **Note:** Depending on the AI assistant, `quickstart` installs ForkFlux skills and MCP server configuration in the folder where you run the command.

The command expects at least two supported CLIs to be available locally: Codex, Claude Code, OpenCode, or Hermes. After it finishes, start the API server in a terminal you keep open:

```bash
uvx --from forkflux-api forkflux serve
```

Then verify the handoff flow with the generated Developer and QA assistants:

1. Open the AI assistant that `quickstart` added to the coordination bus as the Developer agent.
2. Ask it to create a handoff job, for example: `Create status endpoint and handoff to QA`.
3. Open the AI assistant that `quickstart` added to the coordination bus as the QA agent.
4. Ask it to find available jobs, for example: `find available jobs`.
5. Confirm the claim when the QA assistant presents the available job.

For the complete setup guide, including manual MCP configuration, `pip`, custom roles and agents, slash commands, skills, and optional Docker usage, see [QUICK_START.md](QUICK_START.md).

## 🧰 API CLI Commands

The API package includes a Typer-based CLI defined in `packages/api/forkflux_api/cli.py`.

| Command | Purpose |
|---------|---------|
| `forkflux quickstart` | Configure a local demo: apply migrations, create example agents, install skills, and register MCP servers with supported local CLIs. |
| `forkflux init` | Apply migrations and create example roles and agents. |
| `forkflux serve` | Start the API server. |
| `forkflux agents-role list` | List available target roles. |
| `forkflux agents-role add <role_key> <role_label>` | Create a new target role. |
| `forkflux agent list` | List registered agents. |
| `forkflux agent add <agent_label> <role_key> [tool_family]` | Create an agent and generate its API token. |
| `forkflux agent revoke-token <agent_id>` | Revoke an agent token. |

Run the CLI without installing it globally:

```bash
uvx --from forkflux-api forkflux --help
uvx --from forkflux-api forkflux quickstart
```

For manual setup, initialize the database and sample agents yourself:

```bash
uvx --from forkflux-api forkflux init
```

Then start the API server in a terminal you keep open:

```bash
uvx --from forkflux-api forkflux serve
```

Or install the package in your current Python environment:

```bash
pip install forkflux-api
forkflux --help
forkflux quickstart
```

For manual setup, run `forkflux init` instead of `forkflux quickstart`.

Start the API server in a terminal you keep open:

```bash
forkflux serve
```

`forkflux init` applies migrations and creates example roles and agents. `forkflux serve` starts the API server.

`forkflux quickstart` is only for local demo/evaluation. Use the manual commands when you need explicit control over roles, agents, tokens, MCP client configuration, or deployment settings.

Role commands:

```bash
forkflux agents-role list
forkflux agents-role add qa "QA Engineer"
```

Agent commands:

```bash
forkflux agent list
forkflux agent add "Cursor QA Bot" qa --tool_family cursor
forkflux agent revoke-token 1
```

If you are using `uvx` instead of an installed CLI, prefix each command with `uvx --from forkflux-api`, for example `uvx --from forkflux-api forkflux agent list`.

## 🔌 MCP Server

ForkFlux agents connect to the API through the ForkFlux MCP server. The recommended setup runs the MCP server with `uvx` and passes the API connection details through environment variables.

See [QUICK_START.md](QUICK_START.md) for the full MCP client configuration. Use Docker for the MCP server only if your MCP client or deployment environment requires it.

The MCP server exposes these assistant-facing tools:

| Tool | Purpose |
|------|---------|
| `forkflux_create_job` | Publish a structured handoff job with constraints, context, artifacts, priority, and target role. |
| `forkflux_list_jobs` | List jobs available in the shared ForkFlux job pool. |
| `forkflux_claim_job` | Atomically claim a published job and receive its full context payload. |
| `forkflux_change_job_status` | Close claimed work as `completed`, `failed`, or `cancelled`. |

## ⌨️ Automation: Prompts, Commands & Skills

ForkFlux natively integrates with your AI workflows. Depending on your assistant's capabilities (like Claude Code, Cursor, or Cline), you can drive the coordination bus using:

* **Native MCP Prompts:** Automatically exposed to your agent's context workspace (e.g., `/mcp__ff__push`, `/mcp__ff__claim`).
* **Slash Commands:** Drop-in markdown files for custom IDE modes (available in the [`commands/`](commands/) directory).
* **Reusable Skills:** Pre-built sender/receiver workflows for autonomous agents (available in the [`skills/`](skills/) directory).

Use MCP prompts when your assistant supports prompt surfaces, slash commands when your IDE has a command system, and skills when you want reusable sender/receiver workflows across agents.

> 📚 **See the full [Integration & Automation Guide](INTEGRATION.md)** for detailed setup instructions and a complete list of available commands.

## 🤝 Contributing & Community

Our global goal is to make ForkFlux the standard for job exchange in AI-native engineering teams.

* 💬 **Join our Discord:** [https://discord.gg/wTJVctJwn3](https://discord.gg/wTJVctJwn3) - Discuss agent architectures, get direct support from the founders, and share your workflows.
* 🛠 **Contribute:** We welcome Pull Requests, issues, and any ideas on how to improve the agent-to-agent communication protocol. See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## 📄 License

ForkFlux is licensed under Apache-2.0. See [LICENSE](LICENSE) for the full license text.
