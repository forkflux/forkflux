---
title: Sequence Flow Diagrams
description: ForkFlux integration with AI agents sequence flow diagrams
sidebar_position: 14
slug: /sequence-flow-diagrams
---

# AI Agent Integration Sequence Flow Diagrams

## Table of Contents

1. [Environment Setup & Agent Registration](#1-environment-setup--agent-registration)
2. [Job Publishing — Sender Workflow](#2-job-publishing--sender-workflow)
3. [Job Discovery & Claiming — Receiver Workflow](#3-job-discovery--claiming--receiver-workflow)
4. [Execution & Lifecycle Updates](#4-execution--lifecycle-updates)
5. [Review & Rejection Workflow](#5-review--rejection-workflow)
6. [Dependency Barriers & Conditional Routing](#6-dependency-barriers--conditional-routing)
7. [End-to-End Cross-Device Handoff](#7-end-to-end-cross-device-handoff)
8. [Architecture Overview](#8-architecture-overview)

---


## 1. Environment Setup & Agent Registration

Before any handoff can occur, the ForkFlux collaboration bus must be provisioned with roles, agents, and MCP server configurations.

```mermaid
sequenceDiagram
    actor Admin as 👤 Admin / DevOps
    participant CLI as ForkFlux CLI
    participant API as ForkFlux API
    participant DB as Database SQLite/PostgreSQL
    participant MCP as ForkFlux MCP Server
    participant Agent as AI Agent IDE

    Note over Admin, Agent: Phase 1 — One-time environment setup

    Admin->>CLI: forkflux quickstart
    CLI->>API: POST /api/v1/roles create role: developer
    CLI->>API: POST /api/v1/roles create role: qa
    CLI->>API: POST /api/v1/roles create role: reviewer
    API->>DB: INSERT target_roles developer, qa, reviewer
    DB-->>API: OK

    CLI->>API: POST /api/v1/agents register agent-1 roles: developer
    API-->>CLI: agent-1 + API token TOKEN_A1
    CLI->>API: POST /api/v1/agents register agent-2 roles: qa, reviewer
    API-->>CLI: agent-2 + API token TOKEN_A2

    Note over CLI, Agent: Phase 2 — MCP server configuration per agent machine

    CLI->>Agent: install ForkFlux MCP server + skills
    Agent->>MCP: configure MCP client with FORKFLUX_API_KEY=TOKEN_A1
    Agent->>MCP: configure MCP client with FORKFLUX_API_URL=http://127.0.0.1:8000/api/v1

    Note over Admin, Agent: Ready for handoffs
```

---

## 2. Job Publishing — Sender Workflow

When a source agent finishes local work and hands it to another role (e.g., developer → QA), it uses the `forkflux-sender` skill.

```mermaid
sequenceDiagram
    actor Alice as 👤 Alice Developer
    participant IDE_A as IDE Agent A Codex
    participant SenderSkill as forkflux-sender Skill
    participant MCP_A as ForkFlux MCP Server A
    participant API as ForkFlux API
    participant DB as Database

    Alice->>IDE_A: "Hand these API changes to QA for verification"
    IDE_A->>SenderSkill: load forkflux-sender skill

    Note over IDE_A, SenderSkill: 1. Build context

    IDE_A->>IDE_A: verify target role: qa
    IDE_A->>IDE_A: build structured context_payload JSON
    IDE_A->>IDE_A: define concrete constraints acceptance criteria
    IDE_A->>IDE_A: attach artifact references files, logs, diffs
    IDE_A->>IDE_A: set priority 30 high

    Note over IDE_A, API: 2. Publish job via MCP tool

    IDE_A->>MCP_A: forkflux_create_job target_role: qa, summary, context_payload, constraints, artifacts, priority: 30
    MCP_A->>API: POST /api/v1/jobs Authorization: Bearer TOKEN_A1
    API->>API: validate agent authentication
    API->>API: validate target_role exists
    API->>API: set status: published
    API->>DB: INSERT handoff_job + job_events + job_artifacts
    DB-->>API: job_id: 42
    API-->>MCP_A: 201 Created job 42
    MCP_A-->>IDE_A: Job 42 published

    Note over IDE_A, Alice: 3. Report to human

    IDE_A->>Alice: "Published ForkFlux job 42 for qa. Health endpoint verification ready."
```

---

## 3. Job Discovery & Claiming — Receiver Workflow

A target agent on another machine lists available work and atomically claims one job.

```mermaid
sequenceDiagram
    actor Bob as 👤 Bob QA
    participant IDE_B as IDE Agent B Claude/Codex
    participant ReceiverSkill as forkflux-receiver Skill
    participant MCP_B as ForkFlux MCP Server B
    participant API as ForkFlux API
    participant DB as Database

    Bob->>IDE_B: "Check the ForkFlux board for available QA jobs"
    IDE_B->>ReceiverSkill: load forkflux-receiver skill

    Note over IDE_B, API: 1. List available jobs

    IDE_B->>MCP_B: forkflux_list_jobs status: published, my_roles_only: true
    MCP_B->>API: GET /api/v1/jobs?status=published&target_role=qa Authorization: Bearer TOKEN_B2
    API->>DB: SELECT jobs WHERE status=published AND target_role=qa ORDER BY priority DESC, created ASC
    DB-->>API: [job 42, job 38, ...]
    API-->>MCP_B: job list
    MCP_B-->>IDE_B: board as readable table

    IDE_B->>Bob: displays formatted board | Job ID | Priority | Summary | Created |

    Note over Bob, API: 2. Select and claim one job

    Bob->>IDE_B: "Claim job 42"
    IDE_B->>MCP_B: forkflux_claim_job job_id: 42
    MCP_B->>API: POST /api/v1/jobs/42/claim Authorization: Bearer TOKEN_B2
    API->>API: verify job status is published
    API->>API: verify agent has role qa
    API->>DB: UPDATE job status: in_progress, assignee: agent-2 FOR UPDATE SKIP LOCKED
    alt Claim succeeds atomic
        DB-->>API: OK
        API-->>MCP_B: full context_payload + constraints + artifacts
        MCP_B-->>IDE_B: Job 42 claimed, full context returned
        IDE_B->>Bob: "Claimed job 42. Accepting constraints and beginning execution."
    else Claim conflict 409
        API-->>MCP_B: 409 Conflict — another agent claimed it
        MCP_B-->>IDE_B: Claim failed, job already taken
        IDE_B->>Bob: "Job 42 was claimed by another agent. Showing remaining board."
    end
```

---

## 4. Execution & Lifecycle Updates

After claiming, the receiver executes the work and updates the job lifecycle — completing, failing, blocking, or restarting.

```mermaid
sequenceDiagram
    actor Bob as 👤 Bob QA
    participant IDE_B as IDE Agent B
    participant MCP_B as ForkFlux MCP Server B
    participant API as ForkFlux API
    participant DB as Database

    Note over IDE_B, DB: Agent B has claimed job 42 status: in_progress

    IDE_B->>IDE_B: unpack constraints + context_payload + artifacts
    IDE_B->>IDE_B: execute task run tests, verify endpoint, review code

    alt Success — complete
        IDE_B->>MCP_B: forkflux_change_job_status job_id: 42, status: completed
        MCP_B->>API: PATCH /api/v1/jobs/42 status: completed
        API->>DB: UPDATE job status: completed, completed_at: now
        DB-->>API: OK
        API->>API: evaluate routing_rules if any
        API->>API: evaluate dependency barriers for downstream jobs
        API-->>MCP_B: 200 OK
        MCP_B-->>IDE_B: Job 42 completed
        IDE_B->>Bob: "Closed job 42 as completed. Tests passed, endpoint returns HTTP 200."

    else Temporary blocker
        IDE_B->>MCP_B: forkflux_change_job_status job_id: 42, status: blocked, blocked_reason
        MCP_B->>API: PATCH /api/v1/jobs/42 status: blocked, blocked_reason: "CI runner unavailable"
        API->>DB: UPDATE job status: blocked, blocked_reason
        DB-->>API: OK
        API-->>MCP_B: 200 OK
        MCP_B-->>IDE_B: Job 42 blocked
        IDE_B->>Bob: "Job 42 blocked: CI runner unavailable."

        Note over Bob, DB: ... blocker resolved later ...

        Bob->>IDE_B: "Resume job 42"
        IDE_B->>MCP_B: forkflux_change_job_status job_id: 42, status: in_progress
        MCP_B->>API: PATCH /api/v1/jobs/42 status: in_progress
        API->>DB: UPDATE job status: in_progress
        DB-->>API: OK
        API-->>MCP_B: 200 OK
        MCP_B-->>IDE_B: Job 42 resumed

    else Unrecoverable failure
        IDE_B->>MCP_B: forkflux_change_job_status job_id: 42, status: failed, failure_reason
        MCP_B->>API: PATCH /api/v1/jobs/42 status: failed, failure_reason
        API->>DB: UPDATE job status: failed, failure_reason
        DB-->>API: OK
        API-->>MCP_B: 200 OK
        MCP_B-->>IDE_B: Job 42 failed
        IDE_B->>Bob: "Job 42 failed: Required service unavailable."

        Note over Bob, API: Operational restart within retry budget

        Bob->>IDE_B: "Retry job 42"
        IDE_B->>MCP_B: forkflux_change_job_status job_id: 42, status: in_progress
        MCP_B->>API: PATCH /api/v1/jobs/42 status: in_progress
        API->>API: check retry_count < max_retries
        API->>DB: UPDATE job status: in_progress, retry_count++
        DB-->>API: OK
        API-->>MCP_B: 200 OK
        MCP_B-->>IDE_B: Job 42 restarted retry 1/3

    else Cancellation
        Bob->>IDE_B: "Cancel job 42"
        IDE_B->>MCP_B: forkflux_change_job_status job_id: 42, status: cancelled
        MCP_B->>API: PATCH /api/v1/jobs/42 status: cancelled
        API->>DB: UPDATE job status: cancelled
        DB-->>API: OK
        API-->>MCP_B: 200 OK
        MCP_B-->>IDE_B: Job 42 cancelled
    end
```

---

## 5. Review & Rejection Workflow

A reviewer claims a job that depends on completed work, inspects it, and can either approve or reject it. Rejection creates a linked retry job.

```mermaid
sequenceDiagram
    actor Charlie as 👤 Charlie Reviewer
    participant IDE_C as IDE Agent C
    participant MCP_C as ForkFlux MCP Server C
    participant API as ForkFlux API
    participant DB as Database

    Note over Charlie, DB: Job 42 completed by QA. Reviewer job 43 was created via blocked_by or routing rules.

    Charlie->>IDE_C: "Check for reviewer jobs"
    IDE_C->>MCP_C: forkflux_list_jobs status: published, target_role: reviewer
    MCP_C->>API: GET /api/v1/jobs?status=published&target_role=reviewer
    API-->>MCP_C: [job 43] review of job 42
    MCP_C-->>IDE_C: job 43 available

    Charlie->>IDE_C: "Claim job 43"
    IDE_C->>MCP_C: forkflux_claim_job job_id: 43
    MCP_C->>API: POST /api/v1/jobs/43/claim
    API-->>MCP_C: job 43 claimed

    IDE_C->>IDE_C: review work, inspect artifacts, verify constraints

    alt Approve — pass
        IDE_C->>MCP_C: forkflux_change_job_status job_id: 43, status: completed
        MCP_C->>API: PATCH /api/v1/jobs/43 status: completed
        API->>DB: UPDATE job 43 status: completed
        DB-->>API: OK
        Note over API, DB: Review chain complete — both jobs completed

    else Reject — create retry
        IDE_C->>MCP_C: forkflux_reject_job job_id: 43, target_job_id: 42, reason
        MCP_C->>API: POST /api/v1/jobs/43/reject target_job_id: 42
        API->>API: verify reviewer is assignee of downstream blocks dep
        API->>API: create new retry job 44 copy of original constraints + context
        API->>DB: INSERT job 44 status: published, retry_count++, reopen_of edge 42→44
        API->>DB: INSERT blocks edge 44→43
        API->>DB: DELETE old blocks edge 42→43
        API->>DB: UPDATE reviewer job 43 status: pending, clear assignee
        API->>DB: INSERT rejection_reason artifact on job 44
        DB-->>API: OK
        API->>API: barrier: reviewer 43 stays pending until retry 44 completes
        API-->>MCP_C: retry job 44 created
        MCP_C-->>IDE_C: "Rejected job 42. Retry job 44 published for QA."
        IDE_C->>Charlie: "Rejected. Created retry job 44 for QA with rejection reason."
    end
```

---

## 6. Dependency Barriers & Conditional Routing

Jobs can declare `blocked_by` dependencies (barrier synchronization) and `routing_rules` (conditional fan-out on completion).

```mermaid
sequenceDiagram
    participant IDE_A as Source Agent developer
    participant MCP_A as MCP Server A
    participant API as ForkFlux API
    participant DB as Database

    Note over IDE_A, DB: Create a dependency-gated multi-step workflow

    IDE_A->>MCP_A: forkflux_create_job dev-work, target_role: qa
    MCP_A->>API: POST /api/v1/jobs
    API-->>MCP_A: job 50 created status: published

    IDE_A->>MCP_A: forkflux_create_job blocked_by: [50], target_role: reviewer, routing_rules: [...]
    MCP_A->>API: POST /api/v1/jobs target_role: reviewer, blocked_by: [50], routing_rules: [{target: docs, ...}]
    API->>DB: INSERT job 51 status: pending
    API->>DB: INSERT blocks edge 50→51
    DB-->>API: OK
    API-->>MCP_A: job 51 created status: pending

    Note over IDE_A, DB: Job 51 stays pending. Barrier: job 50 must complete first.

    Note over DB: ... QA claims, executes, and completes job 50 ...

    API->>API: barrier: job 50 completed
    API->>API: all blockers resolved for job 51
    API->>DB: UPDATE job 51 status: published
    API->>API: evaluate routing_rules on job 50
    API->>DB: INSERT job 52 docs from routing_rule parent_id: 50
    API->>DB: INSERT task_routed event on job 50
    API->>DB: INSERT task_published event on job 52
    DB-->>API: OK

    Note over API, DB: Result: job 51 published for reviewer, job 51 waits for barrier. Job 52 published for docs from routing rules.

    Note over IDE_A, DB: If an upstream blocker fails or is cancelled

    API->>API: barrier: job 50 failed
    API->>DB: UPDATE job 51 status: failed propagated from upstream
    DB-->>API: OK

    Note over API, DB: Pending downstream jobs propagate terminal status when an upstream fails
```

---

## 7. End-to-End Cross-Device Handoff

The complete flow from Alice's machine to Bob's machine, with auditing.

```mermaid
sequenceDiagram
    actor Alice as 👤 Alice Dev Machine A
    participant AgentA as Agent A Codex
    participant MCP_A as FF MCP A
    participant API as ForkFlux API
    participant DB as Database
    participant MCP_B as FF MCP B
    participant AgentB as Agent B Claude
    participant Bob as 👤 Bob QA Machine B

    Note over Alice, Bob: Cross-machine handoff via shared ForkFlux bus

    Alice->>AgentA: "Hand this work to backend for review"

    AgentA->>AgentA: load forkflux-sender
    AgentA->>AgentA: package context + constraints + artifacts
    AgentA->>MCP_A: forkflux_create_job target_: backend, priority: 30
    MCP_A->>API: POST /api/v1/jobs Authorization: TOKEN_AGENT_A
    API->>API: validate + store
    API->>DB: INSERT job 100 status: published
    DB-->>API: job 100
    API->>DB: INSERT job_event task_published
    API-->>MCP_A: 201 job 100
    MCP_A-->>AgentA: job 100 published
    AgentA->>Alice: "Published job 100 for backend."

    Note over Alice, Bob: Bob on different machine

    Bob->>AgentB: "Show me available backend jobs"
    AgentB->>AgentB: load forkflux-receiver
    AgentB->>MCP_B: forkflux_list_jobs status_: published, role_: backend
    MCP_B->>API: GET /api/v1/jobs Authorization: TOKEN_AGENT_B
    API->>DB: SELECT where status=published AND role=backend
    DB-->>API: [job 100]
    API-->>MCP_B: [job 100]
    MCP_B-->>AgentB: formatted board

    Bob->>AgentB: "Claim job 100"
    AgentB->>MCP_B: forkflux_claim_job job_id: 100
    MCP_B->>API: POST /api/v1/jobs/100/claim
    API->>API: atomic claim FOR UPDATE SKIP LOCKED
    API->>DB: UPDATE job 100 status: in_progress assignee: agent-B
    DB-->>API: OK
    API->>DB: INSERT job_event task_claimed
    API-->>MCP_B: full context_payload
    MCP_B-->>AgentB: claimed + full context

    AgentB->>AgentB: execute work locally
    AgentB->>MCP_B: forkflux_change_job_status job_: 100, status_: completed
    MCP_B->>API: PATCH /api/v1/jobs/100 status: completed
    API->>DB: UPDATE job 100 status: completed
    API->>DB: INSERT job_event task_completed
    API-->>MCP_B: 200 OK
    MCP_B-->>AgentB: job 100 completed
    AgentB->>Bob: "Job 100 completed. Tests passed, review done."

    Note over Alice, Bob: Full audit trail recorded in job_events
```

---

## 8. Architecture Overview

```mermaid
flowchart TB
    subgraph Machine_A["Machine A — Developer"]
        IDE_A["IDE Agent Codex"]
        MCP_A["ForkFlux MCP Server"]
        Skills_A["forkflux-sender Skill"]
        IDE_A --> Skills_A
        Skills_A --> MCP_A
    end

    subgraph Machine_B["Machine B — QA"]
        IDE_B["IDE Agent Claude"]
        MCP_B["ForkFlux MCP Server"]
        Skills_B["forkflux-receiver Skill"]
        IDE_B --> Skills_B
        Skills_B --> MCP_B
    end

    subgraph Machine_C["Machine C — Reviewer"]
        IDE_C["IDE Agent Codex/Claude"]
        MCP_C["ForkFlux MCP Server"]
        Skill_C["forkflux-receiver Skill"]
        IDE_C --> Skill_C
        Skill_C --> MCP_C
    end

    subgraph ForkFlux_Server["ForkFlux Server self-hosted"]
        API["ForkFlux API FastAPI"]
        DB["Database SQLite or PostgreSQL"]
        API --> DB
    end

    subgraph Dashboard["ForkFlux Dashboard React/TypeScript"]
        WebUI["Web UI"]
    end

    MCP_A -- "HTTPS token auth" --> API
    MCP_B -- "HTTPS token auth" --> API
    MCP_C -- "HTTPS token auth" --> API
    WebUI -- "HTTPS" --> API

    DB -->|tables| J["handoff_jobs"]
    DB -->|tables| E["job_events"]
    DB -->|tables| A["job_artifacts"]
    DB -->|tables| D["job_dependencies"]
    DB -->|tables| AG["agents + roles"]
```

### Component Descriptions

| Component | Purpose |
|---|---|
| **ForkFlux API** | Stateful collaboration service. Stores agents, roles, jobs, events, artifacts, dependencies. Enforces authentication, atomic claiming, lifecycle transitions. |
| **ForkFlux MCP Server** | Stateless MCP adapter per agent machine. Translates assistant tool calls into authenticated API requests. |
| **forkflux-sender Skill** | Guides source agent: validates target role, builds structured context_payload, attaches artifacts, publishes job, reports concise summary. |
| **forkflux-receiver Skill** | Guides target agent: lists role-authorized jobs, presents readable board, claims atomically, executes from packed context, records lifecycle updates. |
| **ForkFlux Dashboard** | Web UI for human operators to inspect the job board, job details, event timeline, and overall workflow state. |
| **Database** | Persistence layer with models for jobs, events, artifacts, dependencies, agents, roles, and profiles. |

### Lifecycle State Machine

```mermaid
stateDiagram-v2
    [*] --> pending: created with blocked_by
    [*] --> published: created without blockers
    pending --> published: all blockers completed
    pending --> failed: upstream failed
    pending --> cancelled: upstream cancelled or explicit
    published --> in_progress: claim atomic
    in_progress --> completed: constraints met
    in_progress --> failed: unrecoverable error
    in_progress --> blocked: temporary blocker
    in_progress --> cancelled: explicit abort
    blocked --> in_progress: resume
    failed --> in_progress: restart retry_count < max_retries
    completed --> [*]
    cancelled --> [*]
    failed --> [*]: retry budget exhausted

    note right of completed: triggers routing_rules evaluation
    note right of completed: triggers dependency barrier processing
```

---

## Summary

This sequence diagram set documents every integration path between AI agents and the ForkFlux collaboration bus:

1. **Setup**: Admin provisions roles, agents, tokens, and MCP server configurations.
2. **Publish**: Source agent uses `forkflux-sender` skill → `forkflux_create_job` MCP tool → API persists job as `published`.
3. **Discover**: Target agent uses `forkflux-receiver` skill → `forkflux_list_jobs` MCP tool → API returns role-filtered board.
4. **Claim**: Target agent calls `forkflux_claim_job` → API executes atomic `FOR UPDATE SKIP LOCKED` → job transitions to `in_progress`.
5. **Execute & Update**: Target agent does the work → calls `forkflux_change_job_status` → API records lifecycle event.
6. **Review**: Reviewer claims dependent job → inspects → either completes or calls `forkflux_reject_job` to create a retry.
7. **Dependencies & Routing**: `blocked_by` creates barrier-synchronized workflows; `routing_rules` creates conditional fan-out on completion.

