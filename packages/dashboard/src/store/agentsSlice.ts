/**
 * Registered-agents slice of the global Zustand store.
 *
 * `AgentsPage` is the sole consumer. Unlike roles, agents are mutated by user
 * action (create-agent), so this slice exposes an optimistic `addLocal`
 * helper in addition to the standard `fetch/force/invalidate` cache contract.
 * Roles for the create-agent form come from the shared `rolesSlice`.
 *
 * The in-flight promise lives in slice state (`_inFlight`) rather than a
 * module-level variable so a test-driven `resetStore()` cleanly wipes it —
 * otherwise a "loading" test that never resolves its fetch would pin an
 * in-flight promise for every subsequent test, freezing them on "Loading…".
 * The leading underscore marks it as internal (no selector reads it).
 *
 * Nested under the `agents` key on the store root.
 */

import type { StateCreator } from 'zustand'
import { jobService } from '@job-service'
import type { Agent } from '../types/job.ts'

const CACHE_TTL_MS = 60_000

export interface AgentsState {
  items: Agent[]
  isLoading: boolean
  error: string | null
  fetchedAt: number | null
  /** Internal: the current in-flight fetch promise (for request coalescing). */
  _inFlight: Promise<void> | null
}

export interface AgentsActions {
  fetch: (force?: boolean) => Promise<void>
  invalidate: () => void
  /** Optimistically append a newly created agent without a refetch. */
  addLocal: (agent: Agent) => void
}

export type AgentsSlice = { agents: AgentsState & AgentsActions }

export const createAgentsSlice: StateCreator<
  AgentsSlice,
  [],
  [],
  AgentsSlice
> = (set, get) => ({
  agents: {
    items: [],
    isLoading: false,
    error: null,
    fetchedAt: null,
    _inFlight: null,

    async fetch(force = false) {
      const { fetchedAt, _inFlight } = get().agents
      const fresh = fetchedAt !== null && Date.now() - fetchedAt < CACHE_TTL_MS
      if (!force && fresh) return
      if (_inFlight) return _inFlight

      set((s) => ({ agents: { ...s.agents, isLoading: true, error: null } }))
      const inFlight = jobService
        .fetchAgents()
        .then((data) => {
          set((s) => ({
            agents: {
              ...s.agents,
              items: data,
              fetchedAt: Date.now(),
              isLoading: false,
              _inFlight: null,
            },
          }))
        })
        .catch((err) => {
          set((s) => ({
            agents: {
              ...s.agents,
              isLoading: false,
              error:
                err instanceof Error ? err.message : 'Failed to load agents',
              _inFlight: null,
            },
          }))
        })
      set((s) => ({ agents: { ...s.agents, _inFlight: inFlight } }))
      return inFlight
    },

    invalidate() {
      set((s) => ({ agents: { ...s.agents, fetchedAt: null } }))
    },

    addLocal(agent: Agent) {
      set((s) => ({ agents: { ...s.agents, items: [...s.agents.items, agent] } }))
    },
  },
})
