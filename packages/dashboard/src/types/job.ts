/**
 * Framework-agnostic type definitions for ForkFlux jobs.
 *
 * These types mirror the mock JSON schema in `mocks/jobs.json` and
 * `mocks/details/[id].json`. They contain no React imports and can be
 * extracted into a shared package in a later release.
 */

/** All possible job lifecycle statuses. */
export type JobStatus =
  | 'pending'
  | 'published'
  | 'in_progress'
  | 'completed'
  | 'blocked'
  | 'unblocked'
  | 'failed'
  | 'cancelled';

/** Context payload attached to a job detail. Opaque JSON, like artifact metadata. */
export type ContextPayload = JsonValue;

/**
 * Arbitrary JSON value. Mirrors the backend's `dict[str, Any]` contract for
 * artifact metadata — the shape is intentionally opaque and may vary per
 * artifact, so consumers must narrow at runtime rather than assume fields.
 */
export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };

/** A single event in a job's lifecycle audit trail. */
export interface JobEvent {
  event_type: string;
  current_status: JobStatus;
  actor_agent_label: string | null;
  payload_json: JsonValue;
  created_at: string;
}

/** A single artifact produced by a job. */
export interface JobArtifact {
  type: string;
  uri: string;
  checksum: string | null;
  metadata_json: JsonValue;
}

/** A related job connected to a detail job by a dependency edge. */
export interface JobDependency {
  job_id: number;
  summary: string;
  status: JobStatus;
  target_role_label: string;
  dependency_type: 'blocks' | 'reopen_of';
}

/**
 * A job list item — the lightweight shape returned by the jobs list endpoint.
 */
export interface Job {
  id: number;
  parent_job_id: number | null;
  parent_job_summary: string | null;
  summary: string;
  status: JobStatus;
  priority: number;
  source_agent_label: string;
  assignee_agent_label: string | null;
  target_role_label: string;
  retry_count: number;
  max_retries: number;
  created_at: string;
}

/**
 * A full job detail — the enriched shape returned by the job detail endpoint.
 * Extends the list item with context, constraints, artifacts, lifecycle
 * timestamps, and failure/blocked reasons.
 */
export interface JobDetail extends Job {
  context_payload: ContextPayload;
  constraints: string[];
  routing_rules: JsonValue[] | null;
  artifacts: JobArtifact[];
  events: JobEvent[];
  upstream_dependencies: JobDependency[];
  downstream_dependencies: JobDependency[];
  failure_reason: string | null;
  blocked_reason: string | null;
  unblock_reason: string | null;
  published_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  failed_at: string | null;
  blocked_at: string | null;
  unblocked_at: string | null;
  cancelled_at: string | null;
  expires_at: string | null;
  updated_at: string;
}

/** Filter criteria for the job list. */
export interface JobFilters {
  status: JobStatus | 'all';
  role: string | 'all';
  search: string;
}

/** Sortable fields for the job list. */
export type JobSortField = 'id' | 'summary' | 'status' | 'priority' | 'created_at';

/** Sort direction. */
export type SortDirection = 'asc' | 'desc';

/** A status with its associated count, used for filter pills. */
export interface StatusCount {
  status: JobStatus | 'all';
  count: number;
}

/**
 * Response envelope for the `GET /api/v1/ui/jobs/counts` endpoint.
 *
 * The backend always returns all 7 `JobStatusEnum` values initialized to 0,
 * so consumers can rely on every status being present even when there are
 * no jobs in that state.
 */
export interface JobStatusCountsResponse {
  counts: Record<JobStatus, number>;
}

/**
 * Query params sent to the jobs list endpoint / data source.
 *
 * Combines filtering (status, role, search), sorting (sort + dir), and
 * pagination (limit + offset) into a single object that flows from the URL
 * search params through the data source.
 */
export interface JobListQuery {
  status: JobStatus | 'all';
  role: string | 'all';
  search: string;
  sort: JobSortField;
  dir: SortDirection;
  limit: number;
  offset: number;
}

/**
 * Paginated envelope returned by the jobs list endpoint.
 *
 * `items` is the current page; `total` is the number of rows matching the
 * filters (before pagination); `limit` and `offset` echo the request params.
 */
export interface JobListResponse {
  items: Job[];
  total: number;
  limit: number;
  offset: number;
}

/**
 * Metadata for the job list UI — distinct filter values and per-status counts.
 *
 * Derived from the full (unpaginated) dataset so the status pills and role
 * dropdown stay populated regardless of the current page. The mock computes
 * this from the local JSON; the API data source stubs it until the backend
 * exposes a dedicated metadata endpoint.
 */
export interface JobListMeta {
  statuses: StatusCount[];
  roles: Role[];
}

/**
 * A target role — the structured shape returned by the
 * `GET /api/v1/ui/agents/roles` endpoint.
 *
 * The endpoint requires no authentication and returns a JSON array of
 * these objects. The `role_key` is the stable identifier used as the
 * filter value (sent as `target_role_key` to the jobs list endpoint);
 * `role_label` is the human-readable display text.
 */
export interface Role {
  id: number;
  role_key: string;
  role_label: string;
  created_at: string;
}

/**
 * Request body for the `POST /api/v1/ui/jobs/{job_id}/unblock` endpoint.
 *
 * `unblock_reason` is a required, non-blank string explaining why the job
 * was unblocked. The backend strips and validates it server-side.
 */
export interface UnblockJobRequest {
  unblock_reason: string;
}

/**
 * Response body for the `POST /api/v1/ui/jobs/{job_id}/unblock` endpoint.
 *
 * Returned on a successful unblock (HTTP 200). `previous_status` is always
 * `'blocked'`; `new_status` is always `'unblocked'`.
 */
export interface UnblockJobResponse {
  job_id: number;
  previous_status: JobStatus;
  new_status: JobStatus;
  unblock_reason: string;
}

/**
 * Request body for the `POST /api/v1/ui/agents/roles` endpoint.
 *
 * Both fields are required, non-blank strings (max 255 chars). The
 * `role_key` is the stable identifier; `role_label` is the human-readable
 * display text. Mirrors the backend `CreateRoleRequest` Pydantic schema.
 */
export interface CreateRoleRequest {
  role_key: string;
  role_label: string;
}

/**
 * A role summary attached to an agent — the structured shape nested inside
 * `ListAgentsResponse`. Mirrors the backend `AgentRoleSummary` Pydantic schema.
 */
export interface AgentRoleSummary {
  role_key: string;
  role_label: string;
}

/**
 * An agent — the structured shape returned by the
 * `GET /api/v1/ui/agents` endpoint.
 *
 * The endpoint requires no authentication and returns a JSON array of
 * these objects. `roles` is a list of `AgentRoleSummary` entries describing
 * the target roles this agent can claim jobs for. Mirrors the backend
 * `ListAgentsResponse` Pydantic schema.
 */
export interface Agent {
  id: number;
  agent_label: string;
  tool_family: string | null;
  created_at: string;
  roles: AgentRoleSummary[];
}

/**
 * Request body for the `POST /api/v1/ui/agents` endpoint.
 *
 * `agent_label` is a required, non-blank string (max 255 chars).
 * `tool_family` is an optional string (max 255 chars) identifying the
 * agent's tooling family (e.g. "playwright", "codex").
 * `target_role_ids` is a required list of at least one role ID — the
 * roles this agent is authorized to claim jobs for. Mirrors the backend
 * `CreateAgentRequest` Pydantic schema.
 */
export interface CreateAgentRequest {
  agent_label: string;
  tool_family: string | null;
  target_role_ids: number[];
}

/**
 * Response body for the `POST /api/v1/ui/agents` endpoint.
 *
 * Returned on a successful create (HTTP 201). The `api_token` is a
 * one-time secret — it is returned only in this response and cannot
 * be retrieved again. The UI must surface it to the user immediately
 * with a copy mechanism and a clear warning. Mirrors the backend
 * `CreateAgentResponse` Pydantic schema.
 */
export interface CreateAgentResponse {
  agent_id: number;
  agent_label: string;
  tool_family: string | null;
  target_role_ids: number[];
  api_token: string;
}
