/**
 * Framework-agnostic type definitions for ForkFlux jobs.
 *
 * These types mirror the mock JSON schema in `mocks/jobs.json` and
 * `mocks/details/[id].json`. They contain no React imports and can be
 * extracted into a shared package in a later release.
 */

/** All possible job lifecycle statuses. */
export type JobStatus =
  | 'published'
  | 'claimed'
  | 'in_progress'
  | 'completed'
  | 'blocked'
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

/** A single artifact produced by a job. */
export interface JobArtifact {
  type: string;
  uri: string;
  checksum: string | null;
  metadata_json: JsonValue;
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
  artifacts: JobArtifact[];
  failure_reason: string | null;
  blocked_reason: string | null;
  published_at: string | null;
  claimed_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  failed_at: string | null;
  blocked_at: string | null;
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
  roles: string[];
}

