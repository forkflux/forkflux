/**
 * Data source interface for ForkFlux jobs.
 *
 * Defines the contract that both the mock (local dev) and API (other
 * environments) data sources implement. Consumers depend on this interface,
 * not on a concrete implementation, so swapping data sources is transparent.
 */

import type {
  JobDetail,
  JobListMeta,
  JobListQuery,
  JobListResponse,
  StatusCount,
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
}
