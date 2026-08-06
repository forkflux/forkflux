/**
 * Root of the ForkFlux dashboard global store (Zustand).
 *
 * Combines the in-scope slices (each nested under its own key so they compose
 * without field-name collisions — `items`/`isLoading`/`error`/`fetch` would
 * otherwise clash across slices):
 * - `profile`  — onboarding status (replaces OnboardingGuard local state)
 * - `roles`    — shared target-role cache (RolesPage + AgentsPage)
 * - `agents`   — registered agents (AgentsPage)
 *
 * The deferred `jobs` / `jobCounts` slices (keyed job cache and global status
 * counts) are intentionally NOT included yet — see `plans/react-store.md`.
 * When they land, they compose into this same `create` call, so adding them
 * later is additive and non-breaking.
 *
 * The store is a client of the `jobService` singleton. Slices import
 * `jobService` lazily inside actions so the mock/API data-source switch
 * (driven by `VITE_API_BASE_URL`) remains the single source of truth, and the
 * `JobDataSource` DIP boundary is preserved.
 */

import { create } from 'zustand'
import type { AgentsSlice } from './agentsSlice.ts'
import { createAgentsSlice } from './agentsSlice.ts'
import type { ProfileSlice } from './profileSlice.ts'
import { createProfileSlice } from './profileSlice.ts'
import type { RolesSlice } from './rolesSlice.ts'
import { createRolesSlice } from './rolesSlice.ts'

export type Store = ProfileSlice & RolesSlice & AgentsSlice

export const useStore = create<Store>()((...a) => ({
  ...createProfileSlice(...a),
  ...createRolesSlice(...a),
  ...createAgentsSlice(...a),
}))

/**
 * The initial store state, captured once at module load. Tests call
 * `resetStore()` between cases so the Zustand singleton doesn't leak cached
 * data (e.g. a fresh `fetchedAt` from one test short-circuiting the next
 * test's `fetch()` and hiding its `jobService` mock return value). Production
 * code never calls this — the slices manage their own lifecycle.
 */
const INITIAL_STATE = useStore.getInitialState()

export function resetStore(): void {
  useStore.setState(INITIAL_STATE, true)
}
