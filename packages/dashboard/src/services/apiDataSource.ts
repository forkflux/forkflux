/**
 * API data source — used in non-development environments.
 *
 * Calls the live ForkFlux API. The base URL is configured via the
 * `VITE_API_BASE_URL` environment variable. All endpoints return JSON that
 * matches the types in `src/types/job.ts`.
 *
 * The jobs list endpoint returns a paginated envelope:
 * `{ items, total, limit, offset }`.
 */

import { toStatusCounts } from '../lib/jobs/jobs.ts';
import type {
  JobDetail,
  JobListMeta,
  JobListQuery,
  JobListResponse,
  JobSortField,
  JobStatusCountsResponse,
  Role,
  SortDirection,
  StatusCount,
  UnblockJobRequest,
  UnblockJobResponse,
} from '../types/job.ts';
import type { JobDataSource } from './types.ts';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL as string | undefined;

function getBaseUrl(): string {
  if (!API_BASE_URL) {
    throw new Error(
      'VITE_API_BASE_URL is not set. Configure it for non-dev environments.',
    );
  }
  return API_BASE_URL.replace(/\/$/, '');
}

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Request failed: ${res.status} ${res.statusText} (${url})`);
  }
  return (await res.json()) as T;
}

/**
 * Send a JSON POST request and return the parsed response.
 *
 * Unlike `fetchJson`, this returns the raw `Response` so callers can inspect
 * the status code before deciding how to handle errors (e.g. distinguishing
 * 404 from 422 for the unblock endpoint).
 */
async function postJson(url: string, body: unknown): Promise<Response> {
  return fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

/**
 * Map the dashboard's sort field + direction to the backend's `order` enum
 * values (e.g. `created_at_desc`). The backend accepts repeated `order`
 * query params; we send a single primary order.
 */
function toOrderParam(sort: JobSortField, dir: SortDirection): string {
  return `${sort}_${dir}`;
}

/**
 * Build the query string for the jobs list endpoint from a `JobListQuery`.
 *
 * - `status` is omitted when `all` (no status filter).
 * - `target_role_key` is omitted when `all`.
 * - `search` is omitted when empty — the backend does not yet support a
 *   search param, so client-side search applies to the current page only.
 *   When the backend adds it, send `query.search` here (one-line change).
 * - `my_roles_only=false` — the dashboard is an admin view across all roles.
 */
function buildJobsQueryString(query: JobListQuery): string {
  const params = new URLSearchParams();

  params.set('limit', String(query.limit));
  params.set('offset', String(query.offset));
  params.set('order', toOrderParam(query.sort, query.dir));
  params.set('my_roles_only', 'false');

  if (query.status !== 'all') {
    params.set('status', query.status);
  }
  if (query.role !== 'all') {
    params.set('target_role_key', query.role);
  }

  return params.toString();
}

export const apiDataSource: JobDataSource = {
  fetchJobs(query: JobListQuery): Promise<JobListResponse> {
    const qs = buildJobsQueryString(query);
    return fetchJson<JobListResponse>(`${getBaseUrl()}/ui/jobs?${qs}`);
  },

  /**
   * Fetch the list of target roles from the
   * `GET /api/v1/ui/agents/roles` endpoint.
   *
   * This endpoint requires **no authentication** — no Authorization header is
   * sent. The response is a JSON array of `{ id, role_key, role_label,
   * created_at }` objects. An empty array (HTTP 200 with `[]`) is a valid
   * response when no roles exist.
   *
   * Status counts are now sourced from `fetchJobCounts()` (the dedicated
   * `GET /ui/jobs/counts` endpoint), so `statuses` is left empty here.
   */
  async fetchListMeta(_query: JobListQuery): Promise<JobListMeta> {
    const roles = await fetchJson<Role[]>(
      `${getBaseUrl()}/ui/agents/roles`,
    );
    return { statuses: [], roles };
  },

  /**
   * Fetch global job counts per status from the
   * `GET /api/v1/ui/jobs/counts` endpoint.
   *
   * The backend always returns all 7 `JobStatusEnum` values initialized to
   * 0, so every status is present even when there are no jobs in that
   * state. The response is normalized into a `StatusCount[]` (with an `all`
   * total) via the shared `toStatusCounts` core helper.
   */
  async fetchJobCounts(): Promise<StatusCount[]> {
    const res = await fetchJson<JobStatusCountsResponse>(
      `${getBaseUrl()}/ui/jobs/counts`,
    );
    return toStatusCounts(res.counts as Record<string, number>);
  },

  async fetchJobDetail(id: number): Promise<JobDetail | null> {
    try {
      return await fetchJson<JobDetail>(`${getBaseUrl()}/ui/jobs/${id}`);
    } catch (err) {
      if (err instanceof Error && err.message.includes('404')) return null;
      throw err;
    }
  },

  /**
   * Unblock a blocked job via `POST /api/v1/ui/jobs/{id}/unblock`.
   *
   * Sends the `unblock_reason` as JSON body. On success (200) returns the
   * parsed `UnblockJobResponse`. Throws typed errors for 404 and 422 so the
   * UI can display user-friendly messages:
   * - 404 → "Job not found"
   * - 422 → "This job cannot be unblocked from its current status"
   */
  async unblockJob(
    id: number,
    unblockReason: string,
  ): Promise<UnblockJobResponse> {
    const body: UnblockJobRequest = { unblock_reason: unblockReason };
    const res = await postJson(
      `${getBaseUrl()}/ui/jobs/${id}/unblock`,
      body,
    );

    if (res.status === 404) {
      throw new Error('Job not found');
    }
    if (res.status === 422) {
      throw new Error(
        'This job cannot be unblocked from its current status.',
      );
    }
    if (!res.ok) {
      throw new Error(
        `Request failed: ${res.status} ${res.statusText}`,
      );
    }

    return (await res.json()) as UnblockJobResponse;
  },
};
