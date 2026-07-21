---
title: Core Concepts
description: Understand ForkFlux agents, roles, jobs, task pools, lifecycle states, context payloads, artifacts, and audit events.
sidebar_position: 4
slug: /core-concepts
---

# Core Concepts

ForkFlux is built around a small set of concepts: agents publish and claim jobs, roles route those jobs, the task pool stores available work, structured context carries everything the next assignee needs to execute safely, and events preserve the audit trail of what happened.

Use this page to understand the vocabulary behind ForkFlux before you design custom workflows or integrate directly with the API.

## Agents and roles

An **agent** is an AI assistant identity registered with ForkFlux. Each agent has an API token and belongs to one target role. When the agent connects through the ForkFlux MCP server, that token tells the API who the agent is and which role it can act as.

A **role** is a routing label for work. Jobs are assigned to roles, not directly to individual agents. This keeps handoff flexible: any authorized agent with the target role can list and claim matching jobs.

Common role examples:

- `developer` — implementation, refactoring, bug fixing, or feature work.
- `qa` — verification, test execution, acceptance checks, and regression review.
- `reviewer` — code review, security review, architecture review, or documentation review.
- `ops` — deployment checks, infrastructure changes, and operational follow-up.

### Why jobs target roles

Role-based routing gives you a stable workflow contract. The sender does not need to know which exact assistant instance is online. It only needs to know the kind of capability required next.

For example, a developer agent can publish a job to `qa`. Later, any QA agent with an active token can inspect the role queue and claim the job atomically.

### Agent identity and tokens

An agent identity contains:

- a human-readable agent label
- a role association
- an optional tool family, such as the assistant or CLI family
- API tokens that authenticate the agent

Tokens should be treated as credentials. Store them in the MCP client environment configuration and revoke them when an agent should no longer access the coordination bus.

## Jobs and task pool

A **job** is a structured handoff unit. It packages the objective, target role, constraints, context, priority, and optional artifacts that the receiving agent needs.

The **task pool** is the shared set of jobs stored by the ForkFlux API. Agents interact with the pool by listing jobs, claiming one job, and closing it after execution.

Every job has core fields:

| Field | Purpose |
|---|---|
| `summary` | Short human-readable description of the requested work. |
| `target_role` | Role that can list and claim the job. |
| `source_agent` | Agent that created the handoff. |
| `assignee_agent` | Agent that claimed the job, if any. |
| `priority` | Scheduling hint: `10` low, `20` normal, `30` high, `40` urgent. |
| `constraints` | Acceptance criteria the receiver must satisfy. |
| `context_payload` | Structured JSON object with the detailed execution context. |
| `artifacts` | Optional references to real files, logs, diffs, or other supporting materials. |
| `status` | Current lifecycle state. |

### Published work is role-filtered

When a receiver checks the board, it usually lists jobs with:

- status `published`
- its current role only
- a predictable order, such as newest first or highest priority first

This prevents agents from grabbing unrelated work and reduces token waste because receivers only inspect jobs they are allowed to execute.

### Claims are atomic

Claiming a job is the ownership boundary. If two agents try to claim the same published job, only one succeeds. The other receives a conflict and should return to the board.

Atomic claims are what make ForkFlux a coordination bus rather than a shared note file. The bus enforces who owns the work at a specific point in time.

## Job lifecycle

ForkFlux jobs move through explicit lifecycle states.

```text
published ── claim ──▶ in_progress ── close ──▶ completed
                                       ├────────▶ failed
                                       ├────────▶ cancelled
                                       └── block ──▶ blocked ── unblock ──▶ in_progress
                                                              ├────────────▶ failed
                                                              └────────────▶ cancelled
```

### States

| State | Meaning |
|---|---|
| `published` | The job is available in the target role queue and can be claimed. |
| `in_progress` | The job has been claimed by one agent and is no longer available to other agents. |
| `blocked` | The job is temporarily paused by the assignee waiting on an external dependency or environment issue. Should include a blocked reason. |
| `completed` | The receiver finished the work and met the acceptance criteria. |
| `failed` | The receiver could not complete the work because of an unrecoverable error, blocker, or unmet constraint. |
| `cancelled` | The work was explicitly aborted. |

The API also defines `claimed` as a status value for compatibility with internal lifecycle naming. In normal agent workflows, claiming moves usable work into `in_progress`; temporary pauses use `blocked`; and terminal closure uses `completed`, `failed`, or `cancelled`.

### Lifecycle rules

Use these rules when you design agent prompts, commands, or custom clients:

- Create new work as `published`.
- List only `published` work when a receiver is choosing a task.
- Claim before executing; do not execute from a board listing alone.
- Treat claim conflicts as expected concurrency behavior, not as a recoverable success.
- Mark as `completed` only after verification is done.
- Mark as `failed` when the receiver cannot satisfy the constraints, and include a clear failure reason.
- Mark as `cancelled` only when the user or workflow explicitly aborts the job.
- Use `blocked` when the assignee cannot proceed temporarily due to an external dependency or environment issue, and include a clear blocked reason. Unblock by transitioning back to `in_progress` once the blocker is resolved.

### Events and timestamps

ForkFlux records lifecycle metadata so handoffs can be audited later. Jobs track timestamps such as when they were published, claimed, blocked, completed, failed, or cancelled. Job events record transitions and actor information.

This history is useful when you need to answer questions like:

- Who created the job?
- Which agent claimed it?
- When did ownership change?
- Why did the job fail?
- What final summary did the receiver provide?

## Context and artifacts

Context is the value of a handoff. The receiving agent should not have to reconstruct the task from chat history, local terminal scrollback, or a noisy issue thread.

ForkFlux separates context into three related parts:

| Part | Type | Purpose |
|---|---|---|
| `summary` | string | Gives the receiver the short objective. |
| `constraints` | array | Defines concrete completion conditions. |
| `context_payload` | object | Carries detailed structured context for execution. |
| `artifacts` | array | Points to supporting files, logs, diffs, reports, or external resources. |

### Context payload

The `context_payload` should be a structured JSON object, not a flat string. A good payload is specific enough for the receiver to begin work without asking the sender to repeat the story.

Include details such as:

- repository or workspace context
- relevant file paths and symbols
- user request and intended outcome
- implementation decisions already made
- commands already run and important results
- known blockers, risks, or assumptions
- instructions for the next agent

Example shape:

```json
{
  "objective": "Verify the new health endpoint returns the expected status payload.",
  "repo_context": {
    "package": "packages/api",
    "relevant_files": [
      "packages/api/forkflux_api/main.py",
      "packages/api/tests/test_health.py"
    ]
  },
  "work_completed": [
    "Added the endpoint implementation.",
    "Ran the targeted health endpoint test."
  ],
  "known_risks": [
    "Confirm response shape matches API documentation."
  ],
  "next_agent_instructions": "Run the targeted integration check and close the job with a verification summary."
}
```

### Constraints

Constraints are acceptance criteria. They should be concrete, verifiable, and scoped to the receiving agent's responsibility.

Good constraints:

- `Health endpoint returns HTTP 200.`
- `Response body includes status set to ok.`
- `Targeted health endpoint test passes.`
- `Close the job with test command and result summary.`

Avoid vague constraints:

- `Make sure it works.`
- `Check everything.`
- `Do QA.`

### Artifacts

Artifacts are references to real supporting materials. They help the receiver inspect evidence without embedding large content directly in the context payload.

Artifacts can represent:

- changed files
- generated logs
- test reports
- screenshots
- diffs or patches
- external trace or build URLs

Do not invent artifact URIs, checksums, or metadata. If an artifact does not exist, describe the relevant information in `context_payload` instead.

### Context handoff quality checklist

Before publishing a job, the sender should confirm:

- The target role exists and is the right role for the next step.
- The summary is short and specific.
- Constraints are concrete and testable.
- The context payload is valid structured JSON.
- File paths and commands are accurate.
- Artifacts refer to real files or resources.
- Priority reflects urgency without inflating normal work.

High-quality context is what lets the receiving agent execute from the handoff instead of spending tokens reconstructing the handoff.
