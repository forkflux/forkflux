/**
 * Framework-agnostic business logic for ForkFlux jobs.
 *
 * Every function in this module is pure: it receives data as arguments and
 * returns derived data. There are no React imports and no data-source
 * imports, so this file can be extracted into a shared package and reused
 * by any consumer (dashboard, API client, tests, etc.).
 *
 * The actual data source (mock JSON or live API) is provided by a separate
 * service layer — see `src/services/jobService.ts`.
 */

import type {
  Job,
  JobFilters,
  JobSortField,
  JobStatus,
  SortDirection,
  StatusCount,
} from '../../types/job.ts';

// ---------------------------------------------------------------------------
// Derived collections (dynamic — no hardcoded lists)
// ---------------------------------------------------------------------------

/**
 * Derive the distinct set of statuses present in the data, sorted
 * alphabetically for deterministic filter ordering.
 */
export function getDistinctStatuses(jobs: Job[]): JobStatus[] {
  const grouped = Object.groupBy(jobs, (j) => j.status);
  return Object.keys(grouped).sort() as JobStatus[];
}

/**
 * Count jobs per status, plus an "all" total. Uses `Object.groupBy` to
 * bucket jobs by status, then maps to `{ status, count }` pairs.
 */
export function getStatusCounts(jobs: Job[]): StatusCount[] {
  const grouped = Object.groupBy(jobs, (j) => j.status);

  const result: StatusCount[] = [{ status: 'all', count: jobs.length }];

  for (const status of Object.keys(grouped).sort() as JobStatus[]) {
    result.push({ status, count: grouped[status]!.length });
  }

  return result;
}

/**
 * Canonical lifecycle order of all known job statuses.
 *
 * Used as a display sort key for status pills — a job queue reads more
 * naturally in lifecycle order than alphabetically. This list mirrors the
 * backend `JobStatusEnum`; if the enum grows, the API response is still
 * handled dynamically (unknown statuses are appended after known ones),
 * so a stale list degrades gracefully rather than hiding statuses.
 */
export const JOB_STATUS_ORDER: readonly JobStatus[] = [
  'pending',
  'published',
  'in_progress',
  'blocked',
  'unblocked',
  'completed',
  'failed',
  'cancelled',
];

/**
 * Count jobs per status, returning a dict with **all** known statuses
 * initialized to 0 (mirrors the backend `count_by_status` contract so the
 * mock behaves like the real API). Used by the mock data source.
 */
export function countJobsByStatus(jobs: Job[]): Record<JobStatus, number> {
  const counts = {} as Record<JobStatus, number>;
  for (const status of JOB_STATUS_ORDER) {
    counts[status] = 0;
  }
  for (const job of jobs) {
    counts[job.status] = (counts[job.status] ?? 0) + 1;
  }
  return counts;
}

/**
 * Normalize a raw counts dict (from the API or mock) into a `StatusCount[]`
 * suitable for the status filter pills.
 *
 * - Prepends an `{ status: 'all', count: <sum> }` entry.
 * - Sorts statuses in lifecycle order; any status not in `JOB_STATUS_ORDER`
 *   (e.g. a newly added backend status) is appended alphabetically so it
 *   is never hidden.
 */
export function toStatusCounts(counts: Record<string, number>): StatusCount[] {
  const total = Object.values(counts).reduce((sum, n) => sum + n, 0);
  const result: StatusCount[] = [{ status: 'all', count: total }];

  const known = new Set<string>(JOB_STATUS_ORDER);

  // Known statuses in lifecycle order.
  for (const status of JOB_STATUS_ORDER) {
    if (status in counts) {
      result.push({ status, count: counts[status] });
    }
  }

  // Unknown statuses (not in JOB_STATUS_ORDER) appended alphabetically.
  const unknown = Object.entries(counts)
    .filter(([status]) => !known.has(status))
    .sort((a, b) => a[0].localeCompare(b[0]));
  for (const [status, count] of unknown) {
    result.push({ status: status as JobStatus, count });
  }

  return result;
}

// ---------------------------------------------------------------------------
// Filtering & sorting
// ---------------------------------------------------------------------------

/**
 * Filter a list of jobs by status, role, and free-text search on the summary.
 * Returns a new array — the input is never mutated.
 */
export function filterJobs(jobs: Job[], filters: JobFilters): Job[] {
  const { status, role, search } = filters;
  const needle = search.trim().toLowerCase();

  return jobs.filter((job) => {
    if (status !== 'all' && job.status !== status) return false;
    if (role !== 'all' && job.target_role_label !== role) return false;
    if (needle && !job.summary.toLowerCase().includes(needle)) return false;
    return true;
  });
}

/**
 * Sort a list of jobs by a given field and direction.
 * Returns a new array — the input is never mutated.
 */
export function sortJobs(
  jobs: Job[],
  field: JobSortField,
  direction: SortDirection,
): Job[] {
  return [...jobs].sort((a, b) => {
    let cmp: number;

    if (field === 'id' || field === 'priority') {
      cmp = a[field] - b[field];
    } else if (field === 'created_at') {
      cmp = a.created_at.localeCompare(b.created_at);
    } else {
      // summary, status — string comparison
      cmp = String(a[field]).localeCompare(String(b[field]));
    }

    return direction === 'asc' ? cmp : -cmp;
  });
}

// ---------------------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------------------

/**
 * Format an ISO timestamp into a human-readable date string.
 * Returns an em-dash when the value is null.
 */
export function formatDate(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Format an assignee agent label for display. Returns an em-dash when the
 * value is null (i.e. the job has not been picked up by an agent yet).
 */
export function formatAssignee(label: string | null): string {
  return label ?? '—';
}

/**
 * Format an event type string (e.g. "task_published") into a human-readable
 * label (e.g. "Published").
 */
export function formatEventType(eventType: string): string {
  return eventType
    .replace(/^task_/, '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

/**
 * Format a byte size into a human-readable string (e.g. "1.2 MB").
 */
export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  const value = bytes / Math.pow(1024, i);
  return `${value.toFixed(value >= 100 || i === 0 ? 0 : 1)} ${units[i]}`;
}

// ---------------------------------------------------------------------------
// Role key slugify
// ---------------------------------------------------------------------------

/**
 * Convert a human-readable role label into a slug-safe `role_key`.
 *
 * Lowercases the input, replaces spaces with underscores, and strips any
 * character that is not alphanumeric or an underscore. Leading/trailing
 * underscores are trimmed. Returns an empty string when the input produces
 * no valid characters.
 *
 * Used by the "New Role" form to auto-suggest a `role_key` as the user
 * types a `role_label` — until they manually edit the key field.
 */
export function slugifyRoleKey(label: string): string {
  return label
    .toLowerCase()
    .trim()
    .replace(/\s+/g, '_')
    .replace(/[^a-z0-9_]/g, '')
    .replace(/^_+|_+$/g, '');
}
