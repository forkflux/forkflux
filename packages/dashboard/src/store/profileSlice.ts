/**
 * Onboarding/profile slice of the global Zustand store.
 *
 * Centralizes the onboarding status check that was previously held in
 * `OnboardingGuard` local state and threaded to `OnboardingPage` via
 * `<Outlet context>` callback. The store removes that callback contract:
 * `OnboardingPage` writes `setOnboarded(true)` directly and the guard re-reads
 * `isOnboarded` from the store, so no manual refresh plumbing is required.
 *
 * The slice is a client of the `jobService` singleton (mock or API data
 * source) — it never touches a concrete data source itself, preserving the
 * `JobDataSource` abstraction boundary.
 *
 * Nested under the `profile` key on the store root so it composes with the
 * other namespaced slices (`roles`, `agents`) without field-name collisions.
 */

import type { StateCreator } from 'zustand'
import { jobService } from '@job-service'

export interface ProfileState {
  /** `null` = not yet checked; `true`/`false` = server answer. */
  isOnboarded: boolean | null
  isLoading: boolean
  error: string | null
}

export interface ProfileActions {
  /** Fetch onboarding status from the server. Idempotent; always hits. */
  check: () => Promise<void>
  /** Locally set onboarding status after a successful `createProfile`. */
  setOnboarded: (value: boolean) => void
}

export type ProfileSlice = { profile: ProfileState & ProfileActions }

export const createProfileSlice: StateCreator<
  ProfileSlice,
  [],
  [],
  ProfileSlice
> = (set) => ({
  profile: {
    isOnboarded: null,
    isLoading: false,
    error: null,

    async check() {
      set((s) => ({ profile: { ...s.profile, isLoading: true, error: null } }))
      try {
        const onboarded = await jobService.getProfile()
        set((s) => ({ profile: { ...s.profile, isOnboarded: onboarded, isLoading: false } }))
      } catch (err) {
        set((s) => ({
          profile: {
            ...s.profile,
            isLoading: false,
            error:
              err instanceof Error
                ? err.message
                : 'Failed to check onboarding status',
          },
        }))
      }
    },

    setOnboarded(value: boolean) {
      set((s) => ({ profile: { ...s.profile, isOnboarded: value, error: null } }))
    },
  },
})
