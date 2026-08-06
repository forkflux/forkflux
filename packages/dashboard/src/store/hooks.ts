/**
 * Thin selector hooks over the global Zustand store.
 *
 * Pages import these hooks (never `useStore` directly) so the selector shape
 * is defined in one place and tests can `vi.mock('../../store/hooks')`
 * without touching the store internals.
 *
 * Each hook returns an object bundling the slice's fields + actions its page
 * needs. Returning a fresh object literal every render would make Zustand's
 * `useSyncExternalStore` snapshot comparison see a new value each check and
 * loop (`Maximum update depth exceeded`). We wrap every multi-field selector
 * with `useShallow` so referential inequality only triggers a re-render when
 * one of the selected fields actually changed.
 *
 * Slices are nested under their own keys (`profile`, `roles`, `agents`) on the
 * store root, so the selectors destructure one level deep.
 */

import { useStore } from './index.ts'
import { useShallow } from 'zustand/react/shallow'
import type { Agent, Role } from '../types/job.ts'

export interface UseProfile {
  isOnboarded: boolean | null
  isLoading: boolean
  error: string | null
  check: () => Promise<void>
  setOnboarded: (value: boolean) => void
}

export function useProfile(): UseProfile {
  return useStore(
    useShallow((s) => ({
      isOnboarded: s.profile.isOnboarded,
      isLoading: s.profile.isLoading,
      error: s.profile.error,
      check: s.profile.check,
      setOnboarded: s.profile.setOnboarded,
    })),
  )
}

export interface UseRoles {
  items: Role[]
  isLoading: boolean
  error: string | null
  fetchedAt: number | null
  fetch: (force?: boolean) => Promise<void>
  invalidate: () => void
}

export function useRoles(): UseRoles {
  return useStore(
    useShallow((s) => ({
      items: s.roles.items,
      isLoading: s.roles.isLoading,
      error: s.roles.error,
      fetchedAt: s.roles.fetchedAt,
      fetch: s.roles.fetch,
      invalidate: s.roles.invalidate,
    })),
  )
}

export interface UseAgents {
  items: Agent[]
  isLoading: boolean
  error: string | null
  fetchedAt: number | null
  fetch: (force?: boolean) => Promise<void>
  invalidate: () => void
  addLocal: (agent: Agent) => void
}

export function useAgents(): UseAgents {
  return useStore(
    useShallow((s) => ({
      items: s.agents.items,
      isLoading: s.agents.isLoading,
      error: s.agents.error,
      fetchedAt: s.agents.fetchedAt,
      fetch: s.agents.fetch,
      invalidate: s.agents.invalidate,
      addLocal: s.agents.addLocal,
    })),
  )
}
