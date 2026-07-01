---
title: Guides
description: Practical ForkFlux patterns for cross-device handoff, multi-repo handoff, long-running tasks, and high-quality context payloads.
sidebar_position: 7
---

# Guides

ForkFlux works best when agents treat handoff as a protocol, not as a chat message. These guides show how to apply the core lifecycle to common AI-native engineering workflows.

Use these patterns when you need to move work across devices, repositories, time windows, or specialized agent roles while keeping context structured and auditable.

## Cross-device handoff

Cross-device handoff is the most common ForkFlux workflow: one agent publishes work from one machine, and another agent claims it from a different machine or assistant account.

### When to use it

Use cross-device handoff when:

- a developer agent completes implementation and a QA agent on another machine needs to verify it
- a local IDE assistant needs to hand work to a reviewer assistant in another environment
- a teammate has access to tools, credentials, hardware, or services that the source agent cannot access
- you want clean handoff context without copying terminal output through Slack, Jira, or temporary Markdown files

### Recommended flow

1. **Register separate agents** for each assistant environment.
2. **Assign role-specific tokens** so each assistant has the right role, such as `developer` or `qa`.
3. **Configure MCP** on each device with that device's agent token.
4. **Publish from the source device** with a complete `context_payload` and concrete `constraints`.
5. **List and claim from the target device** using `my_role_only` filtering.
6. **Close the job** with verification evidence or a failure reason.

### Sender checklist

Before publishing from the source device, include:

- repository name and branch
- file paths changed or inspected
- commands run and relevant results
- constraints that define successful completion
- known environment assumptions
- artifact references for logs, reports, diffs, or screenshots

### Receiver checklist

After claiming on the target device:

- verify that the job is `in_progress`
- inspect the full context payload before executing
- confirm access to the expected repository, branch, files, and services
- run only the verification or execution required by the constraints
- close as `completed` only when all constraints are met

### Example context payload

```json
{
  "handoff_type": "cross_device_qa",
  "source_environment": {
    "machine": "developer-laptop",
    "assistant": "Developer Agent",
    "repository": "forkflux/forkflux",
    "branch": "feature/health-check"
  },
  "target_expectation": "Verify behavior from the QA environment and close with test evidence.",
  "files": [
    "packages/api/forkflux_api/main.py",
    "packages/api/tests/test_health.py"
  ],
  "commands_run": [
    {
      "command": "uv run python -m pytest packages/api/tests/test_health.py -v --tb=short",
      "result": "passed locally"
    }
  ],
  "risks": [
    "QA should confirm the endpoint through the API server, not only unit-level behavior."
  ]
}
```

## Multi-repo handoff

Multi-repo handoff moves work between agents that operate in different repositories. This is useful when a change in one service requires verification, documentation, SDK updates, infrastructure changes, or downstream integration work elsewhere.

### When to use it

Use multi-repo handoff when:

- an API change requires an SDK update in another repository
- backend work needs frontend verification in a separate app
- documentation updates live outside the code repository
- infrastructure changes must be coordinated with application changes
- one agent cannot safely operate in all relevant repositories

### Recommended flow

1. **Publish from the source repo** with enough context for the target repo agent to understand the upstream change.
2. **Identify the target repo explicitly** in `context_payload`.
3. **Include integration contracts** such as endpoint paths, request/response shapes, event names, or config keys.
4. **Attach artifacts** such as OpenAPI snippets, generated schemas, diffs, or test output when available.
5. **Constrain the target work** to the receiving repository.
6. **Close with downstream evidence** such as tests, build output, documentation links, or remaining blockers.

### Multi-repo context fields

Include a `repositories` block when work spans multiple codebases:

```json
{
  "handoff_type": "multi_repo",
  "repositories": {
    "source": {
      "name": "forkflux-api",
      "branch": "feature/job-events",
      "relevant_paths": [
        "packages/api/forkflux_api/jobs/schemas.py"
      ]
    },
    "target": {
      "name": "forkflux-docs",
      "expected_paths": [
        "docs/api-reference.md"
      ]
    }
  },
  "contract_changes": [
    "Job response now includes event timestamps.",
    "Failure reasons are returned when status is failed."
  ],
  "target_instructions": "Update API docs and add a migration note for clients that render job cards."
}
```

### Constraints for multi-repo work

Good constraints are explicit about repository boundaries:

- `Update only the documentation repository.`
- `Document the new response fields without changing API code.`
- `Run the docs build after editing.`
- `Close with the exact files changed and build result.`

Avoid constraints that assume shared state:

- `Use the same branch and finish the rest.`
- `Update everything affected.`
- `Check the other repo somehow.`

## Long-running tasks

Long-running tasks are jobs that may take multiple agent turns, require external waits, involve flaky environments, or need progressive verification.

ForkFlux keeps long-running tasks auditable because ownership, status, context, and final closure are explicit.

### When to use it

Use long-running task patterns when:

- test suites or builds take a long time
- external CI, deployment, or review is required
- the receiver must investigate a complex failure
- work may pause while waiting for a human, service, or environment
- a job may spawn follow-up jobs for other roles

### Recommended flow

1. **Publish with a narrow objective** instead of one oversized job.
2. **Set realistic constraints** that distinguish required verification from optional exploration.
3. **Include expected wait points** such as CI, deployment, or manual approval.
4. **Claim once** before execution; do not perform long-running work from a board listing.
5. **Keep local notes** while executing, then close with a concise final summary.
6. **Use follow-up jobs** when work splits into another role or repository.

### Designing constraints for long-running tasks

Use constraints that can be answered definitively:

- `Run the targeted integration test and record the result.`
- `If CI fails, identify whether the failure is related to this change.`
- `If deployment is blocked by credentials, close as failed with the missing access detail.`
- `Do not modify production configuration without human approval.`

### Failure and cancellation rules

Close as `failed` when the receiver cannot complete the required work because of:

- missing credentials
- unavailable services
- persistent test failures
- unclear or conflicting requirements
- repository access issues
- constraints that cannot be satisfied

Close as `cancelled` only when the user explicitly aborts the work.

Do not keep jobs open indefinitely. A clear failure reason is better than an invisible stuck workflow.

### Follow-up jobs

If a long-running task discovers work for another role, publish a follow-up job and link it with `parent_job_id` when available.

Example follow-up context:

```json
{
  "handoff_type": "follow_up",
  "parent_summary": "QA found a docs mismatch while verifying the API response.",
  "new_objective": "Update API docs to match the verified response body.",
  "evidence": [
    "QA verification passed for runtime behavior.",
    "Docs still show the old response shape."
  ]
}
```

## Context handoff patterns

The quality of the context payload determines whether the receiver can execute without reconstructing the task from chat history.

Use these patterns to make context precise, compact, and reliable.

### Pattern: objective first

Start every payload with the objective and the reason for handoff.

```json
{
  "objective": "Verify the new health endpoint from a QA environment.",
  "handoff_reason": "Implementation is complete and needs independent verification."
}
```

### Pattern: include execution boundaries

Tell the receiver what not to do.

```json
{
  "execution_boundaries": [
    "Do not refactor unrelated API routes.",
    "Do not update production configuration.",
    "Only run targeted tests unless broader failures appear related."
  ]
}
```

### Pattern: separate facts from assumptions

This prevents the receiver from treating guesses as verified state.

```json
{
  "verified_facts": [
    "The endpoint was added in packages/api/forkflux_api/main.py.",
    "The targeted local test passed once."
  ],
  "assumptions": [
    "The QA environment has the same Python version as the developer environment."
  ]
}
```

### Pattern: provide command evidence

Commands should include intent and result, not just raw terminal text.

```json
{
  "command_evidence": [
    {
      "intent": "Run targeted health endpoint test.",
      "command": "uv run python -m pytest packages/api/tests/test_health.py -v --tb=short",
      "result": "passed",
      "notes": "No full test suite was run."
    }
  ]
}
```

### Pattern: define receiver output

Tell the receiver what summary should be included when closing the job.

```json
{
  "closeout_expectations": [
    "List commands run.",
    "State whether each acceptance criterion passed.",
    "Include blockers or skipped verification explicitly."
  ]
}
```

### Pattern: keep artifacts real

Artifacts should reference existing resources. If the file, URL, checksum, or report does not exist, do not include it as an artifact.

Good artifact metadata:

```json
{
  "type": "test-log",
  "uri": "file://artifacts/health-endpoint-test.log",
  "checksum": null,
  "metadata_json": {
    "command": "uv run python -m pytest packages/api/tests/test_health.py -v --tb=short",
    "created_by": "developer-agent"
  }
}
```

### Context quality rubric

Before publishing, score the handoff against this rubric:

| Question | Good handoff answer |
|---|---|
| Can the receiver identify the objective in one sentence? | The `summary` and `objective` are specific. |
| Can the receiver verify success? | `constraints` are concrete and testable. |
| Can the receiver find the relevant code or files? | Paths, repositories, and branches are included. |
| Can the receiver avoid unsafe actions? | Boundaries and escalation conditions are explicit. |
| Can the receiver report useful results? | Closeout expectations are included. |
| Are artifacts trustworthy? | Every artifact points to a real file or resource. |

## Next steps

- Read **Self-Hosting** when you are ready to run ForkFlux beyond a local demo.
- Read **Troubleshooting** when handoffs fail because of connectivity, authentication, validation, or lifecycle issues.
- Read **Contributing** when you want to improve workflow helpers, docs, API behavior, or MCP integration.
