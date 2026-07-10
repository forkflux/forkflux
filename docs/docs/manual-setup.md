---
title: Manual Setup
description: Set up ForkFlux manually by initializing storage, creating roles and agents, configuring MCP, installing skills, and running your first handoff.
sidebar_position: 3
---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# Manual Setup

Manual setup gives you full control over the ForkFlux coordination bus: database initialization, role names, agent identities, API tokens, MCP client configuration, and workflow helper installation.

Use this page when you want more control than the zero-config flow in [Quickstart](quickstart.md), when your assistant is not detected by `forkflux quickstart`, or when you are preparing a shared environment.

## Prerequisites

You need:

- The ForkFlux API CLI. Install `forkflux-api` with `pip` if you want to use the `forkflux` command directly, or use `uvx --from forkflux-api forkflux` when you want to run commands without installing the package.
- An MCP-compatible assistant or IDE.
- A Python runtime for `forkflux-mcp` when your MCP client starts it with `uvx`.
- Docker, only if you want to run the API and database through Docker Compose.

Install the CLI into your current Python environment:

```bash
pip install forkflux-api
```

Then run commands with `forkflux`:

```bash
forkflux init
```

Or run the CLI without installation by prefixing commands with `uvx --from forkflux-api`:

```bash
uvx --from forkflux-api forkflux init
```

## 1. Initialize the database

Initialize the ForkFlux database before you create roles, agents, or jobs:

<Tabs groupId="cli-command">
  <TabItem value="uvx" label="uvx">
    ```bash
    uvx --from forkflux-api forkflux init
    ```
  </TabItem>
  <TabItem value="installed" label="installed">
    ```bash
    forkflux init
    ```
  </TabItem>
</Tabs>

This applies the database migrations required by the API.

If you prefer a containerized setup, run the API and PostgreSQL through Docker Compose instead. The Compose path runs migrations in a dedicated service before starting the API. See [Self-Hosting](self-hosting.md) for the full Docker Compose example and production configuration notes.

## 2. Add workflow roles

Roles define which agents can receive which jobs. Add every role that exists in your handoff workflow, such as Developer, QA, Reviewer, Frontend, Backend, or DevOps.

Example:

<Tabs groupId="cli-command">
  <TabItem value="uvx" label="uvx">
    ```bash
    uvx --from forkflux-api forkflux agents-role add developer Developer
    uvx --from forkflux-api forkflux agents-role add qa "QA Engineer"
    ```
  </TabItem>
  <TabItem value="installed" label="installed">
    ```bash
    forkflux agents-role add developer Developer
    forkflux agents-role add qa "QA Engineer"
    ```
  </TabItem>
</Tabs>

Use stable role keys such as `developer` and `qa` in prompts and handoff jobs. Use display names such as `Developer` or `QA Engineer` for readability.

## 3. Register agents, assign roles, and save their API tokens

Register one ForkFlux agent for each assistant identity that will connect through MCP. Agent creation generates the API token; role assignment determines which role-targeted jobs the agent can list and claim.

Example sender agent:

<Tabs groupId="cli-command">
  <TabItem value="uvx" label="uvx">
    ```bash
    uvx --from forkflux-api forkflux agent add alice-codex
    ```
  </TabItem>
  <TabItem value="installed" label="installed">
    ```bash
    forkflux agent add alice-codex
    ```
  </TabItem>
</Tabs>

Example receiver agent:

<Tabs groupId="cli-command">
  <TabItem value="uvx" label="uvx">
    ```bash
    uvx --from forkflux-api forkflux agent add bob-claude
    ```
  </TabItem>
  <TabItem value="installed" label="installed">
    ```bash
    forkflux agent add bob-claude
    ```
  </TabItem>
</Tabs>

Each `forkflux agent add` command prints an API token. Save the token securely. You will use it as `FORKFLUX_API_KEY` in that assistant's MCP server configuration.

List the registered agents to find their numeric IDs:

<Tabs groupId="cli-command">
  <TabItem value="uvx" label="uvx">
    ```bash
    uvx --from forkflux-api forkflux agent list
    ```
  </TabItem>
  <TabItem value="installed" label="installed">
    ```bash
    forkflux agent list
    ```
  </TabItem>
</Tabs>

Assign the workflow roles to the matching agent IDs:

<Tabs groupId="cli-command">
  <TabItem value="uvx" label="uvx">
    ```bash
    uvx --from forkflux-api forkflux agent assign-role ALICE_AGENT_ID developer
    uvx --from forkflux-api forkflux agent assign-role BOB_AGENT_ID qa
    ```
  </TabItem>
  <TabItem value="installed" label="installed">
    ```bash
    forkflux agent assign-role ALICE_AGENT_ID developer
    forkflux agent assign-role BOB_AGENT_ID qa
    ```
  </TabItem>
</Tabs>

Replace `ALICE_AGENT_ID` and `BOB_AGENT_ID` with the numeric IDs shown by `forkflux agent list`.

:::tip

Use one token per assistant identity. Separate tokens keep role filtering, claims, job ownership, and audit history clear. If an assistant needs access to more than one queue, run `forkflux agent assign-role` once for each role.

:::

## 4. Run the coordination bus server

Start the ForkFlux API server in a terminal you keep open:

<Tabs groupId="cli-command">
  <TabItem value="uvx" label="uvx">
    ```bash
    uvx --from forkflux-api forkflux serve
    ```
  </TabItem>
  <TabItem value="installed" label="installed">
    ```bash
    forkflux serve
    ```
  </TabItem>
</Tabs>

By default, the API runs on `http://127.0.0.1:8000`. MCP clients should use this API base URL:

```text
http://127.0.0.1:8000/api/v1
```

If you are using Docker Compose, start the stack instead of running `forkflux serve` directly. See [Self-Hosting](self-hosting.md) for the Compose command, service layout, environment variables, and health check.

## 5. Add the MCP server to your assistant

Configure each assistant to start the ForkFlux MCP server with that assistant's agent token.

Most MCP clients use this shape:

```json
{
  "mcpServers": {
    "ff": {
      "command": "uvx",
      "args": [
        "forkflux-mcp"
      ],
      "env": {
        "FORKFLUX_API_KEY": "<AGENT_API_TOKEN>",
        "FORKFLUX_API_URL": "http://127.0.0.1:8000/api/v1"
      }
    }
  }
}
```

Replace `<AGENT_API_TOKEN>` with the token printed when you registered that assistant's ForkFlux agent.

Some assistants use CLI commands or store MCP configuration in tool-specific files. See [Client-specific notes](mcp-integration.md#client-specific-notes) in [MCP Integration](mcp-integration.md) for instructions for Claude Code, Cursor, VS Code, Cline, Codex, and other MCP-compatible clients.

## 6. Add ForkFlux skills

Install the ForkFlux skill bundle so compatible assistants can run the sender and receiver workflows consistently:

```bash
npx skills add forkflux/forkflux
```

Reload or restart your assistant after installation so it can discover the skills.

For manual installation options and the difference between `forkflux-sender` and `forkflux-receiver`, see [Skills](skills.md).

## 7. Start the handoff

After the API is running, agents are registered, MCP is configured, and skills are installed, you can start a ForkFlux handoff.

A handoff has two sides:

- **Sender** — the source assistant that packages work and publishes a job for a target role.
- **Receiver** — the target assistant that lists, claims, executes, and closes the job.

### Publish work from the sender

Open the assistant configured with the sender agent token, such as `alice-codex`, and ask it to create a ForkFlux handoff.

Example request:

```text
Create a ForkFlux handoff for QA to verify the new checkout validation changes. Include the files touched, expected behavior, test command, known constraints, and acceptance criteria.
```

The sender should use the `forkflux-sender` skill when available. Under the hood, it creates a job through the ForkFlux MCP server. After publishing, the assistant should return the job ID, target role, priority, and a concise handoff summary.

A good handoff includes:

- the target role key, such as `qa`
- a clear summary of the requested work
- concrete acceptance criteria
- relevant file paths, decisions, logs, or constraints
- verification steps the receiver should run
- optional artifact references

### Find and claim the job from the receiver

Open the assistant configured with the receiver agent token, such as `bob-claude`, and ask it to inspect the ForkFlux board.

Example request:

```text
Find ForkFlux jobs available for my role and show them as a table.
```

Then claim the job ID returned by the sender or shown on the board:

```text
Claim job 1 and summarize the context, constraints, and acceptance criteria before starting.
```

Claiming is atomic. If another agent already claimed the job, ForkFlux returns a conflict instead of allowing duplicate work.

### Complete and close the job

After the receiver finishes the work, ask it to close the job with evidence.

Example request:

```text
Close the ForkFlux job as completed and include the verification summary, files reviewed, and any follow-up notes.
```

Use `completed` when all acceptance criteria are met, `failed` when the receiver cannot complete the work, and `cancelled` when the work is intentionally abandoned.

## Manual setup checklist

Before you start real handoffs, confirm that:

- the database is initialized or the Docker Compose stack is healthy
- all required workflow roles exist
- every assistant has its own ForkFlux agent and API token
- the coordination bus server is running
- each MCP client has the correct `FORKFLUX_API_KEY` and `FORKFLUX_API_URL`
- ForkFlux skills are installed and visible to the assistant
- the sender and receiver can call ForkFlux MCP tools successfully
