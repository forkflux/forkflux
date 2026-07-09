---
title: CLI
description: Complete reference for ForkFlux CLI commands, arguments, options, and examples.
sidebar_position: 6
---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# CLI

The ForkFlux CLI manages the API server, database migrations, roles, agents, API tokens, and jobs.

Use this page as a command reference when you need to operate ForkFlux manually. If you want the shortest path to a working demo, start with the [Quickstart guide](quickstart.md).

## Running the CLI

Run the CLI without installing it into your current Python environment:

```bash
uvx --from forkflux-api forkflux --help
```

You can also install `forkflux-api` via pip into an environment and run:

```bash
forkflux --help
```

## Server and setup commands

### `forkflux serve`

Runs database migrations, then starts the ForkFlux API server.

<Tabs groupId="cli-command">
  <TabItem value="uvx" label="uvx">
    ```bash
    uvx --from forkflux-api forkflux serve [OPTIONS]
    ```
  </TabItem>
  <TabItem value="installed" label="installed">
    ```bash
    forkflux serve [OPTIONS]
    ```
  </TabItem>
</Tabs>

| Option | Type | Default | Description |
|---|---:|---:|---|
| `--host` | `TEXT` | `0.0.0.0` | Host interface for the API server to bind to. |
| `--port` | `INTEGER` | `8000` | Port for the API server to listen on. |

Examples:

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

<Tabs groupId="cli-command">
  <TabItem value="uvx" label="uvx">
    ```bash
    uvx --from forkflux-api forkflux serve --host 127.0.0.1 --port 9000
    ```
  </TabItem>
  <TabItem value="installed" label="installed">
    ```bash
    forkflux serve --host 127.0.0.1 --port 9000
    ```
  </TabItem>
</Tabs>

Use this command when you want to run the API locally. MCP clients typically connect to the API base URL ending in `/api/v1`, for example `http://127.0.0.1:8000/api/v1`.

### `forkflux init`

Initializes the database by applying migrations.

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

Arguments: none.

Options: only `--help`.

Use this command before manually creating roles or agents when you do not want to start the API server yet.

### `forkflux quickstart`

Initializes a demo environment with database migrations, example roles, example agents, workflow helpers, and MCP server registrations for supported local assistant CLIs.

<Tabs groupId="cli-command">
  <TabItem value="uvx" label="uvx">
    ```bash
    uvx --from forkflux-api forkflux quickstart
    ```
  </TabItem>
  <TabItem value="installed" label="installed">
    ```bash
    forkflux quickstart
    ```
  </TabItem>
</Tabs>

Arguments: none.

Options: only `--help`.

The command checks for supported assistant CLIs: Codex, Claude Code, OpenCode, and Hermes. At least two supported CLIs must be installed for the automated demo setup.

The quickstart flow creates:

| Resource | Value |
|---|---|
| Role | `developer` / `Developer` |
| Role | `qa` / `QA` |
| Agent | `agent-1` with role `developer` |
| Agent | `agent-2` with role `qa` |

:::caution

`forkflux quickstart` modifies local assistant CLI configuration and installs ForkFlux workflow helpers for supported tools. Use it for local demos and evaluation, not production setup.

:::

### `forkflux stats`

Shows a handoff metrics snapshot for a configurable time window.

Use this command to quickly assess delivery health, queue pressure, and latency trends without querying the database directly.

<Tabs groupId="cli-command">
  <TabItem value="uvx" label="uvx">
    ```bash
    uvx --from forkflux-api forkflux stats [OPTIONS]
    ```
  </TabItem>
  <TabItem value="installed" label="installed">
    ```bash
    forkflux stats [OPTIONS]
    ```
  </TabItem>
</Tabs>

Arguments: none.

| Option | Type | Default | Description |
|---|---:|---:|---|
| `--window-hours` | `INTEGER` | `24` | Metrics lookback window in hours. Must be at least `1`. |
| `--stuck-minutes` | `INTEGER` | `60` | Threshold (minutes) used to classify active jobs as stuck. Must be at least `1`. |
| `--verbose` | `FLAG` | `False` | Shows legacy all-time status counters in an additional table. |

Examples:

<Tabs groupId="cli-command">
  <TabItem value="uvx" label="uvx">
    ```bash
    uvx --from forkflux-api forkflux stats
    ```
  </TabItem>
  <TabItem value="installed" label="installed">
    ```bash
    forkflux stats
    ```
  </TabItem>
</Tabs>

<Tabs groupId="cli-command">
  <TabItem value="uvx" label="uvx">
    ```bash
    uvx --from forkflux-api forkflux stats --window-hours 72 --stuck-minutes 30 --verbose
    ```
  </TabItem>
  <TabItem value="installed" label="installed">
    ```bash
    forkflux stats --window-hours 72 --stuck-minutes 30 --verbose
    ```
  </TabItem>
</Tabs>

The command prints rich tables with the following sections:

| Section | What it shows |
|---|---|
| `Pipeline Health` | Total jobs in the window, completion rate, failure rate, and number of active agents. |
| `Workflow Impact` | Total handoffs and estimated cumulative time saved. |
| `Latency (p50 / p90)` | Median and tail latencies for time-to-claim and time-to-resolution. |
| `Active Queue Snapshot` | Current counts for `published`, `claimed`, and `in_progress`, plus stuck-job count. |
| `Historical (All-time Status Counters)` | Added only with `--verbose`; total counters by job status across all time. |

Operator notes:

- The `Published (waiting)` row appends a bottleneck hint when one role dominates waiting jobs.
- High stuck-job counts usually indicate assignment imbalance, blocked dependencies, or missing agent capacity.

## Role commands

Role commands are grouped under `forkflux agents-role`. A role defines the type of work an agent can target or receive, such as `developer`, `qa`, `frontend`, or `reviewer`.

### `forkflux agents-role list`

Lists all registered target roles.

<Tabs groupId="cli-command">
  <TabItem value="uvx" label="uvx">
    ```bash
    uvx --from forkflux-api forkflux agents-role list
    ```
  </TabItem>
  <TabItem value="installed" label="installed">
    ```bash
    forkflux agents-role list
    ```
  </TabItem>
</Tabs>

Arguments: none.

Options: only `--help`.

Output includes each role key and label.

### `forkflux agents-role add`

Creates a new target role.

<Tabs groupId="cli-command">
  <TabItem value="uvx" label="uvx">
    ```bash
    uvx --from forkflux-api forkflux agents-role add ROLE_KEY ROLE_LABEL
    ```
  </TabItem>
  <TabItem value="installed" label="installed">
    ```bash
    forkflux agents-role add ROLE_KEY ROLE_LABEL
    ```
  </TabItem>
</Tabs>

| Argument | Type | Required | Description |
|---|---|---:|---|
| `ROLE_KEY` | `TEXT` | Yes | Stable machine-readable key used by jobs and agents. |
| `ROLE_LABEL` | `TEXT` | Yes | Human-readable role name shown in CLI output. |

Options: only `--help`.

Examples:

<Tabs groupId="cli-command">
  <TabItem value="uvx" label="uvx">
    ```bash
    uvx --from forkflux-api forkflux agents-role add developer Developer
    ```
  </TabItem>
  <TabItem value="installed" label="installed">
    ```bash
    forkflux agents-role add developer Developer
    ```
  </TabItem>
</Tabs>

<Tabs groupId="cli-command">
  <TabItem value="uvx" label="uvx">
    ```bash
    uvx --from forkflux-api forkflux agents-role add qa "Quality Assurance"
    ```
  </TabItem>
  <TabItem value="installed" label="installed">
    ```bash
    forkflux agents-role add qa "Quality Assurance"
    ```
  </TabItem>
</Tabs>

Use a concise lowercase key for `ROLE_KEY` because agents and jobs reference this value.

### `forkflux agents-role delete`

Deletes a target role by key.

<Tabs groupId="cli-command">
  <TabItem value="uvx" label="uvx">
    ```bash
    uvx --from forkflux-api forkflux agents-role delete ROLE_KEY
    ```
  </TabItem>
  <TabItem value="installed" label="installed">
    ```bash
    forkflux agents-role delete ROLE_KEY
    ```
  </TabItem>
</Tabs>

| Argument | Type | Required | Description |
|---|---|---:|---|
| `ROLE_KEY` | `TEXT` | Yes | Role key to delete. |

Options: only `--help`.

Example:

<Tabs groupId="cli-command">
  <TabItem value="uvx" label="uvx">
    ```bash
    uvx --from forkflux-api forkflux agents-role delete qa
    ```
  </TabItem>
  <TabItem value="installed" label="installed">
    ```bash
    forkflux agents-role delete qa
    ```
  </TabItem>
</Tabs>

The command asks for confirmation before deleting. ForkFlux refuses to delete a role while agents or other records still use it.

## Agent commands

Agent commands are grouped under `forkflux agent`. An agent represents an assistant identity that can authenticate to ForkFlux and perform work for a role.

### `forkflux agent list`

Lists all registered agents.

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

Arguments: none.

Options: only `--help`.

Output includes each agent ID, label, and role key.

### `forkflux agent add`

Creates an agent and generates an API token for it.

<Tabs groupId="cli-command">
  <TabItem value="uvx" label="uvx">
    ```bash
    uvx --from forkflux-api forkflux agent add [OPTIONS] AGENT_LABEL ROLE_KEY
    ```
  </TabItem>
  <TabItem value="installed" label="installed">
    ```bash
    forkflux agent add [OPTIONS] AGENT_LABEL ROLE_KEY
    ```
  </TabItem>
</Tabs>

| Argument | Type | Required | Description |
|---|---|---:|---|
| `AGENT_LABEL` | `TEXT` | Yes | Human-readable label for the agent. |
| `ROLE_KEY` | `TEXT` | Yes | Existing role key assigned to the agent. |

| Option | Type | Default | Description |
|---|---:|---:|---|
| `--tool-family` | `TEXT` | none | Optional assistant/tool family identifier, such as `claude`, `codex`, `opencode`, or `hermes`. |

Examples:

<Tabs groupId="cli-command">
  <TabItem value="uvx" label="uvx">
    ```bash
    uvx --from forkflux-api forkflux agent add alice-codex developer
    ```
  </TabItem>
  <TabItem value="installed" label="installed">
    ```bash
    forkflux agent add alice-codex developer
    ```
  </TabItem>
</Tabs>

<Tabs groupId="cli-command">
  <TabItem value="uvx" label="uvx">
    ```bash
    uvx --from forkflux-api forkflux agent add bob-claude qa --tool-family claude
    ```
  </TabItem>
  <TabItem value="installed" label="installed">
    ```bash
    forkflux agent add bob-claude qa --tool-family claude
    ```
  </TabItem>
</Tabs>

The command prints the generated API key. Save it immediately and configure it in the agent's MCP client environment as `FORKFLUX_API_KEY`.

### `forkflux agent revoke-token`

Revokes the API token associated with an agent.

<Tabs groupId="cli-command">
  <TabItem value="uvx" label="uvx">
    ```bash
    uvx --from forkflux-api forkflux agent revoke-token AGENT_ID
    ```
  </TabItem>
  <TabItem value="installed" label="installed">
    ```bash
    forkflux agent revoke-token AGENT_ID
    ```
  </TabItem>
</Tabs>

| Argument | Type | Required | Description |
|---|---|---:|---|
| `AGENT_ID` | `INTEGER` | Yes | Numeric ID of the agent whose token should be revoked. |

Options: only `--help`.

Example:

<Tabs groupId="cli-command">
  <TabItem value="uvx" label="uvx">
    ```bash
    uvx --from forkflux-api forkflux agent revoke-token 2
    ```
  </TabItem>
  <TabItem value="installed" label="installed">
    ```bash
    forkflux agent revoke-token 2
    ```
  </TabItem>
</Tabs>

After revocation, the agent can no longer authenticate with the old token.

## Job commands

Job commands are grouped under `forkflux job`. A job is a structured handoff record with a lifecycle status, target role, context payload, and optional artifacts.

### `forkflux job list`

Lists jobs in the coordination bus.

<Tabs groupId="cli-command">
  <TabItem value="uvx" label="uvx">
    ```bash
    uvx --from forkflux-api forkflux job list [OPTIONS]
    ```
  </TabItem>
  <TabItem value="installed" label="installed">
    ```bash
    forkflux job list [OPTIONS]
    ```
  </TabItem>
</Tabs>

| Option | Type | Default | Description |
|---|---:|---:|---|
| `--limit` | `INTEGER` | `50` | Maximum number of jobs to show. |
| `--status` | `CHOICE` | none | Filter by job status. Accepted values: `published`, `claimed`, `in_progress`, `completed`, `failed`, `cancelled`. |
| `--target-role-key` | `TEXT` | none | Filter jobs by target role key. |

Examples:

<Tabs groupId="cli-command">
  <TabItem value="uvx" label="uvx">
    ```bash
    uvx --from forkflux-api forkflux job list
    ```
  </TabItem>
  <TabItem value="installed" label="installed">
    ```bash
    forkflux job list
    ```
  </TabItem>
</Tabs>

<Tabs groupId="cli-command">
  <TabItem value="uvx" label="uvx">
    ```bash
    uvx --from forkflux-api forkflux job list --status published --target-role-key qa --limit 10
    ```
  </TabItem>
  <TabItem value="installed" label="installed">
    ```bash
    forkflux job list --status published --target-role-key qa --limit 10
    ```
  </TabItem>
</Tabs>

Output includes job ID, summary, status, priority, source agent, assignee, target role, and creation time.

### `forkflux job details`

Prints full job details as formatted JSON.

<Tabs groupId="cli-command">
  <TabItem value="uvx" label="uvx">
    ```bash
    uvx --from forkflux-api forkflux job details JOB_ID
    ```
  </TabItem>
  <TabItem value="installed" label="installed">
    ```bash
    forkflux job details JOB_ID
    ```
  </TabItem>
</Tabs>

| Argument | Type | Required | Description |
|---|---|---:|---|
| `JOB_ID` | `INTEGER` | Yes | Numeric job ID to inspect. |

Options: only `--help`.

Example:

<Tabs groupId="cli-command">
  <TabItem value="uvx" label="uvx">
    ```bash
    uvx --from forkflux-api forkflux job details 42
    ```
  </TabItem>
  <TabItem value="installed" label="installed">
    ```bash
    forkflux job details 42
    ```
  </TabItem>
</Tabs>

Use this command when you need the complete context payload, artifacts, lifecycle data, or event history for a job.

### `forkflux job delete`

Deletes a job by ID.

<Tabs groupId="cli-command">
  <TabItem value="uvx" label="uvx">
    ```bash
    uvx --from forkflux-api forkflux job delete JOB_ID
    ```
  </TabItem>
  <TabItem value="installed" label="installed">
    ```bash
    forkflux job delete JOB_ID
    ```
  </TabItem>
</Tabs>

| Argument | Type | Required | Description |
|---|---|---:|---|
| `JOB_ID` | `INTEGER` | Yes | Numeric job ID to delete. |

Options: only `--help`.

Example:

<Tabs groupId="cli-command">
  <TabItem value="uvx" label="uvx">
    ```bash
    uvx --from forkflux-api forkflux job delete 42
    ```
  </TabItem>
  <TabItem value="installed" label="installed">
    ```bash
    forkflux job delete 42
    ```
  </TabItem>
</Tabs>

The command asks for confirmation before deleting. ForkFlux refuses to delete a job when deletion would violate lifecycle or parent-child constraints.

### `forkflux job change-status`

Changes a job's lifecycle status on behalf of an agent.

<Tabs groupId="cli-command">
  <TabItem value="uvx" label="uvx">
    ```bash
    uvx --from forkflux-api forkflux job change-status [OPTIONS] JOB_ID STATUS AGENT_ID
    ```
  </TabItem>
  <TabItem value="installed" label="installed">
    ```bash
    forkflux job change-status [OPTIONS] JOB_ID STATUS AGENT_ID
    ```
  </TabItem>
</Tabs>

| Argument | Type | Required | Description |
|---|---|---:|---|
| `JOB_ID` | `INTEGER` | Yes | Numeric job ID to update. |
| `STATUS` | `CHOICE` | Yes | New status. Accepted values: `published`, `claimed`, `in_progress`, `completed`, `failed`, `cancelled`. |
| `AGENT_ID` | `INTEGER` | Yes | Numeric ID of the agent performing the status change. |

| Option | Type | Default | Description |
|---|---:|---:|---|
| `--failure-reason` | `TEXT` | none | Optional explanation for failed or blocked work. |

Examples:

<Tabs groupId="cli-command">
  <TabItem value="uvx" label="uvx">
    ```bash
    uvx --from forkflux-api forkflux job change-status 42 in_progress 2
    ```
  </TabItem>
  <TabItem value="installed" label="installed">
    ```bash
    forkflux job change-status 42 in_progress 2
    ```
  </TabItem>
</Tabs>

<Tabs groupId="cli-command">
  <TabItem value="uvx" label="uvx">
    ```bash
    uvx --from forkflux-api forkflux job change-status 42 completed 2
    ```
  </TabItem>
  <TabItem value="installed" label="installed">
    ```bash
    forkflux job change-status 42 completed 2
    ```
  </TabItem>
</Tabs>

<Tabs groupId="cli-command">
  <TabItem value="uvx" label="uvx">
    ```bash
    uvx --from forkflux-api forkflux job change-status 42 failed 2 --failure-reason "Acceptance tests are blocked by missing credentials."
    ```
  </TabItem>
  <TabItem value="installed" label="installed">
    ```bash
    forkflux job change-status 42 failed 2 --failure-reason "Acceptance tests are blocked by missing credentials."
    ```
  </TabItem>
</Tabs>

Prefer terminal statuses for final outcomes:

| Status | Use when |
|---|---|
| `completed` | The receiving agent completed the work and met the acceptance criteria. |
| `failed` | The receiving agent cannot complete the work because of an unrecoverable issue. |
| `cancelled` | The user or workflow explicitly abandoned the work. |

## Manual setup example

This sequence initializes ForkFlux, creates a custom role, creates an agent for that role, and starts the API server.

<Tabs groupId="cli-command">
  <TabItem value="uvx" label="uvx">
    ```bash
    uvx --from forkflux-api forkflux init
    uvx --from forkflux-api forkflux agents-role add reviewer Reviewer
    uvx --from forkflux-api forkflux agent add reviewer-claude reviewer --tool-family claude
    uvx --from forkflux-api forkflux serve
    ```
  </TabItem>
  <TabItem value="installed" label="installed">
    ```bash
    forkflux init
    forkflux agents-role add reviewer Reviewer
    forkflux agent add reviewer-claude reviewer --tool-family claude
    forkflux serve
    ```
  </TabItem>
</Tabs>

Copy the API key printed by `forkflux agent add` into the MCP client configuration for the receiving assistant.
