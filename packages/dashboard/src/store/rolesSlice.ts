/**
 * Target-roles slice of the global Zustand store.
 *
 * The role list is shared, immutable, and read by more than one page:
 * `RolesPage` lists roles and `AgentsPage` lists roles in its create-agent
 * form. Previously each page fetched roles independently, so switching tabs
 * re-fetched the same list. This slice caches the result and lets both pages
 * share one fetch — `AgentsPage` reuses `useRoles` instead of calling
 * `jobService.fetchRoles` itself.
 *
 * `fetch(force)` skips the network when a fresh result is already cached
 * (controlled by `CACHE_TTL_MS`), unless `force` is true. `invalidate()`
 * clears the cache so the next `fetch` hits the server (used after a create).
 *
 * The in-flight promise lives in slice state (`_inFlight`) rather than a
 * module-level variable so a test-driven `resetStore()` cleanly wipes it —
 * otherwise a "loading" test that never resolves its fetch would leave an
 * in-flight promise pinned for every subsequent test, freezing them on
 * "Loading…". The leading underscore marks it as internal (no selector reads it).
 *
 * Nested under the `roles` key on the store root.
 */

import type { StateCreator } from 'zustand'
import { jobService } from '@job-service'
import type { Role } from '../types/job.ts'

/** Reuse a fresh cached list for this long before refetching. */
const CACHE_TTL_MS = 60_000

export interface RolesState {
  items: Role[]
  isLoading: boolean
  error: string | null
  /** Epoch ms of the last successful fetch; `null` = never fetched. */
  fetchedAt: number | null
  /** Internal: the current in-flight fetch promise (for request coalescing). */
  _inFlight: Promise<void> | null
}

export interface RolesActions {
  /**
   * Fetch roles, reusing a fresh cache unless `force` is true.
   * Concurrent callers share a single in-flight request.
   */
  fetch: (force?: boolean) => Promise<void>
  /** Clear the cache; the next `fetch` will hit the server. */
  invalidate: () => void
}

export type RolesSlice = { roles: RolesState & RolesActions }

export const createRolesSlice: StateCreator<RolesSlice, [], [], RolesSlice> = (
  set,
  get,
) => ({
  roles: {
    items: [],
    isLoading: false,
    error: null,
    fetchedAt: null,
    _inFlight: null,

    async fetch(force = false) {
      const { fetchedAt, _inFlight } = get().roles
      const fresh = fetchedAt !== null && Date.now() - fetchedAt < CACHE_TTL_MS
      if (!force && fresh) return
      if (_inFlight) return _inFlight

      set((s) => ({ roles: { ...s.roles, isLoading: true, error: null } }))
      const inFlight = jobService
        .fetchRoles()
        .then((data) => {
          set((s) => ({
            roles: {
              ...s.roles,
              items: data,
              fetchedAt: Date.now(),
              isLoading: false,
              _inFlight: null,
            },
          }))
        })
        .catch((err) => {
          set((s) => ({
            roles: {
              ...s.roles,
              isLoading: false,
              error: err instanceof Error ? err.message : 'Failed to load roles',
              _inFlight: null,
            },
          }))
        })
      set((s) => ({ roles: { ...s.roles, _inFlight: inFlight } }))
      return inFlight
    },

    invalidate() {
      set((s) => ({ roles: { ...s.roles, fetchedAt: null } }))
    },
  },
})
