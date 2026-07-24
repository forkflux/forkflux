/**
 * Data source interface for ForkFlux jobs.
 *
 * Defines the contract that both the mock (local dev) and API (other
 * environments) data sources implement. Consumers depend on this interface,
 * not on a concrete implementation, so swapping data sources is transparent.
 */

import type {
  Agent,
  CreateAgentResponse,
  JobDetail,
  JobListMeta,
  JobListQuery,
  JobListResponse,
  Role,
  StatusCount,
  UnblockJobResponse,
} from '../types/job.ts';

export interface JobDataSource {
  /** Fetch a single page of jobs matching the query. */
  fetchJobs(query: JobListQuery): Promise<JobListResponse>;

  /**
   * Fetch list UI metadata: distinct roles for the role dropdown.
   *
   * Status counts are now sourced from `fetchJobCounts()` (the dedicated
   * `GET /api/v1/ui/jobs/counts` endpoint), so this method focuses on
   * role metadata. The `statuses` field of the returned `JobListMeta` is
   * no longer populated by data sources.
   */
  fetchListMeta(query: JobListQuery): Promise<JobListMeta>;

  /**
   * Fetch global job counts per status from the
   * `GET /api/v1/ui/jobs/counts` endpoint.
   *
   * Returns a `StatusCount[]` (including an `all` total) with all known
   * statuses present — the backend always returns every status initialized
   * to 0. Counts are global (independent of role/search/status filters).
   */
  fetchJobCounts(): Promise<StatusCount[]>;

  /** Fetch a single job detail by id. Returns null when not found. */
  fetchJobDetail(id: number): Promise<JobDetail | null>;

  /**
   * Fetch all available target roles from the
   * `GET /api/v1/ui/agents/roles` endpoint.
   *
   * Returns a `Role[]` with `role_key` and `role_label` for each role.
   * An empty array is a valid response when no roles exist.
   */
  fetchRoles(): Promise<Role[]>;

  /**
   * Fetch all registered agents from the
   * `GET /api/v1/ui/agents` endpoint.
   *
   * Returns an `Agent[]` with `id`, `agent_label`, `tool_family`,
   * `created_at`, and `roles` (a list of `AgentRoleSummary` with `role_key`
   * and `role_label`). An empty array is a valid response when no agents
   * exist.
   */
  fetchAgents(): Promise<Agent[]>;

  /**
   * Create a new target role via `POST /api/v1/ui/agents/roles`.
   *
   * Sends `role_key` and `role_label` as JSON body. On success (201)
   * returns the created `Role`. Throws a typed error on 409/422 (duplicate
   * `role_key`) so the UI can display a user-friendly message.
   */
  createRole(roleKey: string, roleLabel: string): Promise<Role>;

  /**
   * Create a new agent via `POST /api/v1/ui/agents`.
   *
   * Sends `agent_label`, `tool_family`, and `target_role_ids` as JSON body.
   * On success (201) returns a `CreateAgentResponse` that includes the
   * one-time `api_token` — this token is only available in this response
   * and cannot be retrieved again. Throws a typed error on 422 (role not
   * found or validation) so the UI can display a user-friendly message.
   */
  createAgent(
    agentLabel: string,
    toolFamily: string | null,
    targetRoleIds: number[],
  ): Promise<CreateAgentResponse>;

  /**
   * Unblock a blocked job by providing an unblock reason.
   *
   * Calls `POST /api/v1/ui/jobs/{id}/unblock`. Throws a typed error on
   * 404 (job not found) or 422 (job is not in BLOCKED status) so the UI
   * can display a user-friendly message.
   */
  unblockJob(id: number, unblockReason: string): Promise<UnblockJobResponse>;
}
