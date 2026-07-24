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
 */

import {
  countJobsByStatus,
  filterJobs,
  getDistinctRoles,
  sortJobs,
  toStatusCounts,
} from '../lib/jobs/jobs.ts';
import type {
  Job,
  JobDetail,
  JobListMeta,
  JobListQuery,
  JobListResponse,
  StatusCount,
} from '../types/job.ts';
import type { JobDataSource } from './types.ts';

import jobsData from '../../mocks/jobs.json' with { type: 'json' };

// The mock JSON is the full dataset; cast once at module load.
const ALL_JOBS = jobsData as Job[];

export const mockDataSource: JobDataSource = {
  fetchJobs(query: JobListQuery): Promise<JobListResponse> {
    // 1. Filter by status, role, and search (server-side semantics).
    const filtered = filterJobs(ALL_JOBS, {
      status: query.status,
      role: query.role,
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
    // Roles are independent of the active filters and derived from the full
    // dataset. Status counts are now sourced from `fetchJobCounts()` (the
    // dedicated counts endpoint), so `statuses` is left empty here.
    const roles = getDistinctRoles(ALL_JOBS);

    return Promise.resolve({ statuses: [], roles });
  },

  /**
   * Global job counts per status over the full mock dataset. Mirrors the
   * backend `count_by_status` contract: all 7 statuses are present,
   * initialized to 0 when there are no jobs in that state.
   */
  fetchJobCounts(): Promise<StatusCount[]> {
    return Promise.resolve(toStatusCounts(countJobsByStatus(ALL_JOBS)));
  },

  async fetchJobDetail(id: number): Promise<JobDetail | null> {
    try {
      const mod = await import(
        /* @vite-ignore */ `../../mocks/details/${id}.json`
      );
      return mod.default as JobDetail;
    } catch {
      return null;
    }
  },
};
