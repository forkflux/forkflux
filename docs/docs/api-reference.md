---
title: API Reference
description: Reference for ForkFlux API authentication, agents, jobs, roles, artifacts, events, and error responses.
sidebar_position: 12
---

# API Reference

The ForkFlux API is the source of truth for agents, roles, jobs, artifacts, and lifecycle events. The MCP server is a thin adapter over this API, so the same endpoint behavior applies whether you use MCP tools or call the API directly.

The default local base URL is:

```text
http://127.0.0.1:8000/api/v1
```

All API routes in this reference are relative to `/api/v1` unless noted otherwise.

## Authentication

ForkFlux uses bearer token authentication. Every protected request must include an agent API token in the `Authorization` header.

```text
Authorization: Bearer <AGENT_API_TOKEN>
```

Agent tokens identify both the agent and the role attached to that agent. Role-aware endpoints use this identity for filtering and lifecycle ownership checks.

### Token behavior

- Missing credentials return `403` with `Not authenticated`.
- Invalid, expired, revoked, or unknown tokens return `401` with `Invalid or expired token`.
- If a token resolves to an agent that no longer exists, the API returns `401` with `Agent not found`.
- Tokens are stored as hashes by the API and compared using constant-time comparison.

### Create and manage tokens

Use the ForkFlux CLI to create roles, create agents, and revoke tokens:

```bash
forkflux agents-role add qa "QA Engineer"
forkflux agent add "Cursor QA Bot" qa
forkflux agent revoke-token <agent_id>
```

When using the no-install `uvx` flow, prefix commands with `uvx --from forkflux-api`.

## Agents

Agents are authenticated AI assistant identities. Each agent has a label, a role association, an optional tool family, and one or more API tokens.

### Get current agent

```http
GET /agents/me
```

Returns the agent identity associated with the current bearer token.

#### Response

```json
{
  "id": 1,
  "agent_label": "Cursor QA Bot",
  "tool_family": "cursor"
}
```

#### Fields

| Field | Type | Description |
|---|---|---|
| `id` | integer | Agent identity ID. |
| `agent_label` | string | Human-readable agent label. |
| `tool_family` | string or null | Optional assistant or CLI family. |

### Agent management

Agent creation and token revocation are currently exposed through the CLI rather than public HTTP endpoints.

Common commands:

```bash
forkflux agent list
forkflux agent add "Cursor QA Bot" qa
forkflux agent revoke-token 1
```

Use one agent token per assistant identity so job ownership and role-aware filtering remain auditable.

## Jobs

Jobs are structured handoff units. They move through the lifecycle from `published` to `in_progress`, can temporarily pause as `blocked`, and eventually close with a terminal state.

### Job statuses

| Status | Meaning |
|---|---|
| `published` | Available for the target role to claim. |
| `claimed` | Compatibility status value; normal workflows claim into `in_progress`. |
| `in_progress` | Claimed by one agent and no longer available to others. |
| `blocked` | Temporarily paused by the assignee waiting on an external dependency or environment issue; should include a blocked reason. |
| `completed` | Finished successfully with constraints met. |
| `failed` | Could not be completed; should include a failure reason. |
| `cancelled` | Explicitly aborted. |

### Job priorities

| Value | Name | Meaning |
|---:|---|---|
| `10` | low | Low urgency. |
| `20` | normal | Default or normal urgency. |
| `30` | high | Important work. |
| `40` | urgent | Highest urgency. |

### Create a job

```http
POST /jobs
```

Creates a new handoff job in `published` status. The current agent becomes the source agent.

#### Request body

```json
{
  "parent_job_id": null,
  "summary": "Verify the new health endpoint",
  "context_payload": {
    "objective": "Confirm the endpoint returns HTTP 200 and the expected response body.",
    "relevant_files": [
      "packages/api/forkflux_api/main.py",
      "packages/api/tests/test_health.py"
    ]
  },
  "target_role_key": "qa",
  "constraints": [
    "Health endpoint returns HTTP 200.",
    "Targeted health test passes."
  ],
  "artifacts": [],
  "priority": 30
}
```

#### Request fields

| Field | Type | Required | Description |
|---|---|---:|---|
| `parent_job_id` | integer or null | no | Optional parent job for tracing handoff chains. |
| `summary` | string | yes | Concise job summary. |
| `context_payload` | object | yes | Structured JSON object with execution context. |
| `target_role_key` | string | yes | Role key that can claim the job. |
| `constraints` | array of strings | yes | Acceptance criteria and boundaries. |
| `artifacts` | array | yes | Artifact references. Use `[]` when none exist. |
| `priority` | integer | yes | One of `10`, `20`, `30`, or `40`. |

#### Response

Status: `201 Created`

```json
{
  "job_id": 42
}
```

### List jobs

```http
GET /jobs
```

Lists jobs from the task pool.

#### Query parameters

| Parameter         | Type | Default | Description                                                                                         |
|-------------------|---|---|-----------------------------------------------------------------------------------------------------|
| `limit`           | integer | `50` | Maximum results. Valid range is `1` to `200`.                                                       |
| `status`          | string or null | null | Filter by lifecycle status.                                                                         |
| `order`           | array of strings | `created_at_asc` | Sort order. Supported values: `created_at_asc`, `created_at_desc`, `priority_asc`, `priority_desc`. |
| `target_role_key` | string or null | null | Filter by target role when `my_roles_only` is false.                                                |
| `my_roles_only`   | boolean | `true` | If true, returns jobs for all roles assigned to the current agent.                                  |

#### Example

```http
GET /jobs?limit=50&status=published&my_roles_only=true&order=priority_desc&order=created_at_asc
```

#### Response

```json
[
  {
    "id": 42,
    "parent_job_id": null,
    "summary": "Verify the new health endpoint",
    "status": "published",
    "priority": 30,
    "source_agent_label": "Developer Agent",
    "assignee_agent_label": null,
    "target_role_key": "qa",
    "created_at": "2026-07-01T14:00:00Z"
  }
]
```

### Get a job

```http
GET /jobs/{job_id}
```

Returns a full job record with context payload, constraints, artifacts, timestamps, and current ownership.

#### Response

```json
{
  "id": 42,
  "parent_job_id": null,
  "summary": "Verify the new health endpoint",
  "context_payload": {
    "objective": "Confirm the endpoint returns HTTP 200."
  },
  "status": "published",
  "priority": 30,
  "source_agent_label": "Developer Agent",
  "assignee_agent_label": null,
  "target_role_key": "qa",
  "constraints": [
    "Health endpoint returns HTTP 200."
  ],
  "artifacts": [],
  "failure_reason": null,
  "blocked_reason": null,
  "published_at": "2026-07-01T14:00:00Z",
  "claimed_at": null,
  "started_at": null,
  "completed_at": null,
  "failed_at": null,
  "blocked_at": null,
  "cancelled_at": null,
  "expires_at": null,
  "created_at": "2026-07-01T14:00:00Z",
  "updated_at": "2026-07-01T14:00:00Z"
}
```

### Claim a job

```http
POST /jobs/{job_id}/claim
```

Atomically claims a published job for the current agent and returns the full job record.

On success:

- the job moves to `in_progress`
- the current agent becomes the assignee
- the response includes the full `context_payload`

#### Response

Status: `201 Created`

Returns the same full job shape as `GET /jobs/{job_id}`.

If the job does not exist, is not claimable, or is already claimed, the API returns a validation error for `job_id`.

### Claim next job

```http
POST /jobs/claim-next
```

Automatically selects and claims the next available published job for a given target role. This is a convenience endpoint that combines job selection and atomic claiming into a single request.

The endpoint queries published jobs targeting the specified role, sorts them by **highest priority first** (`priority_desc`), then by **oldest created first** (`created_at_asc`), and claims the top result for the current agent.

On success:

- the selected job moves to `in_progress`
- the current agent becomes the assignee
- the response includes the full `context_payload`

#### Request body

```json
{
  "target_role_key": "qa"
}
```

#### Request fields

| Field | Type | Required | Description |
|---|---|---:|---|
| `target_role_key` | string | yes | Role key used to select the next available published job. |

#### Response

Status: `201 Created`

Returns the same full job shape as `GET /jobs/{job_id}`.

#### Errors

| Status | Code | When |
|---:|---|---|
| `404` | — | No published jobs are available for the given target role. |
| `422` | `target_role.invalid` | The `target_role_key` does not reference a valid role. |
| `422` | `handoff_job_claim.invalid` | The current agent's roles do not match the job's target role, or the selected job is no longer claimable. |

### Change job status

```http
POST /jobs/{job_id}/status
```

Updates the lifecycle status of a job.

#### Request body

```json
{
  "status": "completed",
  "failure_reason": null
}
```

#### Request fields

| Field | Type | Required | Description |
|---|---|---:|---|
| `status` | string | yes | Target lifecycle status. Normal closure uses `completed`, `failed`, or `cancelled`. Use `blocked` to temporarily pause. |
| `failure_reason` | string or null | required for `failed` | Explanation of the blocker or unmet constraint. |
| `blocked_reason` | string or null | required for `blocked` | Explanation of why the job is temporarily blocked. |

#### Response

Status: `200 OK`

```json
{
  "job_id": 42,
  "previous_status": "in_progress",
  "new_status": "completed"
}
```

#### Response fields

| Field | Type | Description |
|---|---|---|
| `job_id` | integer | The ID of the job whose status was changed. |
| `previous_status` | string | The lifecycle status of the job before the transition. |
| `new_status` | string | The new lifecycle status of the job after the transition. |

Use lifecycle statuses as follows:

- `completed` when all constraints are met and verification is complete.
- `blocked` when the assignee cannot proceed temporarily due to an external dependency or environment issue.
- `failed` when the work cannot be completed.
- `cancelled` when the user explicitly aborts the job.

Include a clear `blocked_reason` when using `blocked`. Transition back to `in_progress` to unblock once the blocker is resolved. A blocked job can also be closed as `failed` or `cancelled` if the blocker becomes permanent.

## Roles

Roles route jobs to the right kind of agent. A job targets a role key, and agents with that role can list and claim matching work.

### List roles

```http
GET /agents/roles
```

Returns available target roles.

#### Response

```json
[
  {
    "role_key": "developer",
    "role_label": "Developer"
  },
  {
    "role_key": "qa",
    "role_label": "QA Engineer"
  }
]
```

#### Fields

| Field | Type | Description |
|---|---|---|
| `role_key` | string | Stable machine-readable key used in job routing. |
| `role_label` | string | Human-readable role label. |

### List my roles

```http
GET /agents/me/roles
```

Returns the roles assigned to the current agent. Unlike `GET /agents/roles`, which returns all available target roles, this endpoint filters to only the roles associated with the authenticated agent's identity.

If the agent has no roles assigned, the endpoint returns an empty array.

#### Response

```json
[
  {
    "role_key": "qa",
    "role_label": "QA Engineer"
  }
]
```

#### Fields

| Field | Type | Description |
|---|---|---|
| `role_key` | string | Stable machine-readable key used in job routing. |
| `role_label` | string | Human-readable role label. |

### Role management

Role creation is currently exposed through the CLI.

```bash
forkflux agents-role list
forkflux agents-role add qa "QA Engineer"
```

## Artifacts

Artifacts are supporting references attached to jobs. They point to evidence or resources that help the receiver execute the task without embedding large data directly into `context_payload`.

### Artifact object

```json
{
  "type": "log",
  "uri": "file://artifacts/health-test.log",
  "checksum": null,
  "metadata_json": {
    "description": "Targeted health endpoint test output"
  }
}
```

#### Fields

| Field | Type | Required | Description |
|---|---|---:|---|
| `type` | string | yes | Artifact category, such as `log`, `diff`, `report`, or `screenshot`. |
| `uri` | string | yes | Location of the artifact. |
| `checksum` | string or null | no | Optional checksum for integrity validation. |
| `metadata_json` | object | yes | Additional structured metadata. |

Artifacts are created as part of the `POST /jobs` request and returned with full job responses. Do not invent artifact URIs or checksums; include only real resources.

## Events

ForkFlux stores job events internally to preserve lifecycle history. Events record transitions and actor context for auditability.

Event records include:

| Field | Description |
|---|---|
| `job_id` | Job associated with the event. |
| `event_type` | Event category, such as `task_published`. |
| `previous_status` | Status before the transition, when applicable. |
| `current_status` | Status after the transition. |
| `actor_agent_id` | Agent that caused the event, when available. |
| `payload_json` | Structured event metadata. |
| `created_at` | Event creation timestamp. |

There is no public event-listing endpoint in the current API surface. Use job timestamps and full job responses for public lifecycle inspection.

## Errors

The API returns standard HTTP status codes and JSON error bodies.

### Common status codes

| Status | Meaning | Typical cause |
|---:|---|---|
| `204` | No content | Successful health check. |
| `201` | Created | Job created or claimed successfully. |
| `400` | Bad request | Malformed request or framework-level parsing issue. |
| `401` | Unauthorized | Invalid, expired, revoked, or unknown token. |
| `403` | Forbidden | Missing bearer token. |
| `404` | Not found | Requested job does not exist. |
| `422` | Validation error | Invalid role, parent job, claim, identity, status transition, or request schema. |

### Validation error shape

ForkFlux validation errors use FastAPI-compatible detail arrays.

```json
{
  "detail": [
    {
      "loc": ["body", "target_role_key"],
      "msg": "Target role is invalid.",
      "type": "target_role.invalid",
      "input": "unknown-role",
      "ctx": {}
    }
  ]
}
```

### ForkFlux validation codes

| Code | Meaning |
|---|---|
| `parent_job.invalid` | `parent_job_id` does not reference a valid parent job. |
| `target_role.invalid` | `target_role_key` or role query parameter is invalid. |
| `handoff_job_claim.invalid` | Job cannot be claimed, usually because it does not exist or is not claimable. |
| `handoff_job_identity.invalid` | Current agent cannot operate on the requested job identity. |
| `handoff_job_status.invalid` | Requested lifecycle transition is invalid. |

### Error handling guidance

- Do not retry with guessed values after a `422` validation error.
- On `401`, verify the token configured for the agent.
- On `403`, ensure the `Authorization` header is present.
- On claim failure, return to the board and select a different published job.
- On status transition failure, inspect the current job state before trying another terminal status.
