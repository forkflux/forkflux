/**
 * Mock data source — local development only.
 *
 * Reads from the JSON files in `mocks/`. The list and roles are imported
 * statically (bundled at build time); detail files are loaded on demand via
 * Vite's dynamic `import()` so only the requested detail is fetched.
 *
 * The list endpoint simulates server-side filtering, sorting, and pagination
 * over the full local dataset so dev mode behaves like the real API: the
 * caller receives a single page plus a `total` count.
 *
 * An in-memory overlay (`jobOverlay`) tracks mutations from `unblockJob`
 * so that subsequent `fetchJobDetail` / `fetchJobs` / `fetchJobCounts` calls
 * reflect the updated state — mirroring how the real API persists changes.
 */

import {
  countJobsByStatus,
  filterJobs,
  sortJobs,
  toStatusCounts,
} from '../lib/jobs/jobs.ts';
import type {
  Job,
  JobDetail,
  JobListMeta,
  JobListQuery,
  JobListResponse,
  Role,
  StatusCount,
  UnblockJobResponse,
} from '../types/job.ts';
import type { JobDataSource } from './types.ts';

import jobsData from '../../mocks/jobs.json' with { type: 'json' };
import rolesData from '../../mocks/roles.json' with { type: 'json' };

// The mock JSON is the full dataset; cast once at module load.
const ALL_JOBS = jobsData as Job[];
const ALL_ROLES = rolesData as Role[];

/**
 * In-memory overlay for mutated job state.
 *
 * When a job is unblocked (or otherwise mutated), the changes are written
 * here keyed by job ID. `fetchJobDetail`, `fetchJobs`, and `fetchJobCounts`
 * all merge this overlay with the static JSON so the UI reflects mutations
 * without reloading the page.
 */
const jobOverlay = new Map<number, Partial<JobDetail>>();

/**
 * Return a copy of a job with any overlay mutations applied.
 * Used by `fetchJobs` and `fetchJobCounts` to reflect in-memory state.
 */
function applyOverlayToJob(job: Job): Job {
  const overlay = jobOverlay.get(job.id);
  if (!overlay) return job;
  return { ...job, ...overlay };
}

/**
 * Return a copy of a job detail with any overlay mutations applied.
 * Used by `fetchJobDetail` to reflect in-memory state.
 */
function applyOverlayToDetail(detail: JobDetail): JobDetail {
  const overlay = jobOverlay.get(detail.id);
  if (!overlay) return detail;
  return { ...detail, ...overlay };
}

/**
 * Reset the in-memory overlay. Test-only utility to ensure test isolation —
 * the module-level `jobOverlay` Map persists across tests otherwise.
 */
export function __resetMockState(): void {
  jobOverlay.clear();
}

export const mockDataSource: JobDataSource = {
  fetchJobs(query: JobListQuery): Promise<JobListResponse> {
    // The role filter value is a `role_key` (e.g. "frontend"), but mock jobs
    // only carry `target_role_label`. Resolve the key to its label so the
    // existing `filterJobs` (which compares labels) works correctly.
    let roleLabel = query.role;
    if (query.role !== 'all') {
      const match = ALL_ROLES.find((r) => r.role_key === query.role);
      roleLabel = match ? match.role_label : query.role;
    }

    // Apply overlay mutations to the static dataset before filtering.
    const jobsWithOverlay = ALL_JOBS.map(applyOverlayToJob);

    // 1. Filter by status, role, and search (server-side semantics).
    const filtered = filterJobs(jobsWithOverlay, {
      status: query.status,
      role: roleLabel,
      search: query.search,
    });

    // 2. Sort by the requested field/direction.
    const sorted = sortJobs(filtered, query.sort, query.dir);

    const total = sorted.length;

    // 3. Clamp offset into [0, total] so an out-of-range offset (e.g. after a
    //    filter narrows results) yields an empty page rather than throwing.
    const safeOffset = Math.min(Math.max(query.offset, 0), total);
    const items = sorted.slice(safeOffset, safeOffset + query.limit);

    return Promise.resolve({
      items,
      total,
      limit: query.limit,
      offset: safeOffset,
    });
  },

  fetchListMeta(_query: JobListQuery): Promise<JobListMeta> {
    // Roles are sourced from the mock roles JSON (mirrors the
    // `GET /api/v1/ui/agents/roles` endpoint). Status counts are now sourced
    // from `fetchJobCounts()` (the dedicated counts endpoint), so `statuses`
    // is left empty here.
    return Promise.resolve({ statuses: [], roles: ALL_ROLES });
  },

  /**
   * Global job counts per status over the full mock dataset. Mirrors the
   * backend `count_by_status` contract: all 7 statuses are present,
   * initialized to 0 when there are no jobs in that state.
   *
   * Applies the in-memory overlay so counts reflect mutations (e.g. a job
   * unblocked in the current session moves from `blocked` to `unblocked`).
   */
  fetchJobCounts(): Promise<StatusCount[]> {
    const jobsWithOverlay = ALL_JOBS.map(applyOverlayToJob);
    return Promise.resolve(toStatusCounts(countJobsByStatus(jobsWithOverlay)));
  },

  async fetchJobDetail(id: number): Promise<JobDetail | null> {
    try {
      const mod = await import(
        /* @vite-ignore */ `../../mocks/details/${id}.json`
      );
      const detail = mod.default as JobDetail;
      // Merge any in-memory overlay mutations (e.g. from unblockJob).
      return applyOverlayToDetail(detail);
    } catch {
      return null;
    }
  },

  /**
   * Unblock a blocked job (mock). Mirrors the API data source contract:
   * returns a mock `UnblockJobResponse` with `new_status: 'unblocked'`
   * and `previous_status: 'blocked'`. Throws the same typed errors as the
   * API source for 404/422 parity.
   *
   * Persists the mutation to the in-memory overlay so subsequent
   * `fetchJobDetail` calls return the updated `unblocked` status,
   * `unblock_reason`, and `unblocked_at` — mirroring the real API.
   */
  async unblockJob(
    id: number,
    unblockReason: string,
  ): Promise<UnblockJobResponse> {
    // Simulate a small delay for realism.
    await new Promise((r) => setTimeout(r, 100));

    const staticJob = ALL_JOBS.find((j) => j.id === id);
    if (!staticJob) {
      throw new Error('Job not found');
    }

    // Check the overlay-mutated state, not the static JSON.
    const job = applyOverlayToJob(staticJob);
    if (job.status !== 'blocked') {
      throw new Error(
        'This job cannot be unblocked from its current status.',
      );
    }

    // Persist the mutation to the in-memory overlay.
    const now = new Date().toISOString();
    jobOverlay.set(id, {
      status: 'unblocked',
      unblock_reason: unblockReason,
      unblocked_at: now,
      blocked_reason: null,
      blocked_at: null,
      updated_at: now,
    });

    return {
      job_id: id,
      previous_status: 'blocked',
      new_status: 'unblocked',
      unblock_reason: unblockReason,
    };
  },
};
