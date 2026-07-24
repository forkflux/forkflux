/**
 * `useJobListParams` — URL search params ↔ `JobListQuery` bridge.
 *
 * Reads `status`, `role`, `search`, `sort`, `dir`, `limit`, and `offset` from
 * the URL search params and exposes typed setters that write back to the URL.
 *
 * Changing any **filter** (status, role, search, sort, dir) resets `offset`
 * to `0`, because the result set changes and the old offset is no longer
 * meaningful. Changing `limit` also resets `offset` to `0`.
 *
 * The URL is the single source of truth: filters and pagination are
 * shareable/bookmarkable, and back/forward navigation works as expected.
 */

import { useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import type {
  JobListQuery,
  JobSortField,
  JobStatus,
  SortDirection,
} from '../../types/job.ts';

// ---------------------------------------------------------------------------
// Defaults & allowed values
// ---------------------------------------------------------------------------

const DEFAULT_LIMIT = 50;
const DEFAULT_OFFSET = 0;
const DEFAULT_SORT: JobSortField = 'created_at';
const DEFAULT_DIR: SortDirection = 'desc';

const SORT_FIELDS: readonly JobSortField[] = [
  'id',
  'summary',
  'status',
  'priority',
  'created_at',
];

const SORT_DIRS: readonly SortDirection[] = ['asc', 'desc'];

const JOB_STATUSES: readonly (JobStatus | 'all')[] = [
  'all',
  'published',
  'claimed',
  'in_progress',
  'completed',
  'blocked',
  'failed',
  'cancelled',
];

// ---------------------------------------------------------------------------
// Parsing helpers
// ---------------------------------------------------------------------------

function parseString<T extends string>(
  value: string | null,
  allowed: readonly T[],
  fallback: T,
): T {
  return value && (allowed as readonly string[]).includes(value) ? (value as T) : fallback;
}

function parseIntParam(value: string | null, fallback: number): number {
  if (value === null) return fallback;
  const n = Number(value);
  return Number.isFinite(n) && n >= 0 ? Math.floor(n) : fallback;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export interface UseJobListParams {
  query: JobListQuery;
  setStatus: (status: JobStatus | 'all') => void;
  setRole: (role: string | 'all') => void;
  setSearch: (search: string) => void;
  setSort: (field: JobSortField) => void;
  setDir: (dir: SortDirection) => void;
  setOffset: (offset: number) => void;
  setLimit: (limit: number) => void;
}

export function useJobListParams(): UseJobListParams {
  const [searchParams, setSearchParams] = useSearchParams();

  const query: JobListQuery = useMemo(() => {
    const status = parseString(searchParams.get('status'), JOB_STATUSES, 'all');
    const role = searchParams.get('role') ?? 'all';
    const search = searchParams.get('search') ?? '';
    const sort = parseString(searchParams.get('sort'), SORT_FIELDS, DEFAULT_SORT);
    const dir = parseString(searchParams.get('dir'), SORT_DIRS, DEFAULT_DIR);
    const limit = parseIntParam(searchParams.get('limit'), DEFAULT_LIMIT);
    const offset = parseIntParam(searchParams.get('offset'), DEFAULT_OFFSET);

    return { status, role, search, sort, dir, limit, offset };
  }, [searchParams]);

  /**
   * Merge a partial update into the current search params.
   *
   * `resetOffset` controls whether `offset` is cleared to `0` — true for any
   * filter or limit change, false for pure offset changes.
   */
  const update = useCallback(
    (patch: Partial<JobListQuery>, resetOffset: boolean) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);

          // Apply each provided field, deleting the param when it matches the
          // default so the URL stays clean. Each value is captured into a
          // const so TypeScript narrows away `undefined` (the `in` check
          // alone does not, because Partial values are `T | undefined`).
          const { status, role, search, sort, dir, limit, offset } = patch;

          if (status !== undefined) {
            if (status === 'all') {
              next.delete('status');
            } else {
              next.set('status', status);
            }
          }
          if (role !== undefined) {
            if (role === 'all') {
              next.delete('role');
            } else {
              next.set('role', role);
            }
          }
          if (search !== undefined) {
            if (search === '') {
              next.delete('search');
            } else {
              next.set('search', search);
            }
          }
          if (sort !== undefined) {
            if (sort === DEFAULT_SORT) {
              next.delete('sort');
            } else {
              next.set('sort', sort);
            }
          }
          if (dir !== undefined) {
            if (dir === DEFAULT_DIR) {
              next.delete('dir');
            } else {
              next.set('dir', dir);
            }
          }
          if (limit !== undefined) {
            if (limit === DEFAULT_LIMIT) {
              next.delete('limit');
            } else {
              next.set('limit', String(limit));
            }
          }

          // Offset handling: explicit value, or reset to 0.
          if (offset !== undefined) {
            if (offset === DEFAULT_OFFSET) {
              next.delete('offset');
            } else {
              next.set('offset', String(offset));
            }
          } else if (resetOffset) {
            next.delete('offset');
          }

          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  const setStatus = useCallback(
    (status: JobStatus | 'all') => update({ status }, true),
    [update],
  );

  const setRole = useCallback(
    (role: string | 'all') => update({ role }, true),
    [update],
  );

  const setSearch = useCallback(
    (search: string) => update({ search }, true),
    [update],
  );

  const setSort = useCallback(
    (field: JobSortField) => update({ sort: field }, true),
    [update],
  );

  const setDir = useCallback(
    (dir: SortDirection) => update({ dir }, true),
    [update],
  );

  const setOffset = useCallback(
    (offset: number) => update({ offset }, false),
    [update],
  );

  const setLimit = useCallback(
    (limit: number) => update({ limit }, true),
    [update],
  );

  return {
    query,
    setStatus,
    setRole,
    setSearch,
    setSort,
    setDir,
    setOffset,
    setLimit,
  };
}
