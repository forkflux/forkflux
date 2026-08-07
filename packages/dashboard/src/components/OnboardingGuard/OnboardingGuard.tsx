import { useEffect } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useProfile } from '../../store/hooks'

/**
 * Layout-route wrapper that checks onboarding status on mount.
 *
 * - While loading: renders a centered spinner.
 * - If `is_onboarded === false` and NOT already on `/onboarding`:
 *   redirects to `/onboarding`.
 * - If `is_onboarded === true` and ON `/onboarding`:
 *   redirects to `/jobs`.
 * - Otherwise: renders child routes via `<Outlet />`.
 *
 * Onboarding status lives in the global store `profileSlice`. `OnboardingPage`
 * writes `setOnboarded(true)` directly after `createProfile` succeeds, so this
 * guard no longer needs to expose an `Outlet context` refresh callback — the
 * store propagation replaces the old `refreshProfile` plumbing.
 */
export function OnboardingGuard() {
  const location = useLocation()
  const { isOnboarded, error, check } = useProfile()

  useEffect(() => {
    void check()
  }, [check])

  // ── loading ────────────────────────────────────────────────────
  // Stay in loading until the onboarding status is known (`null` before
  // `check()` flips `isLoading`, during the in-flight request, or even if
  // `isLoading` never gets set) and no error has surfaced. Once a boolean or
  // error arrives the guard resolves to its normal redirect/outlet paths.
  if (isOnboarded === null && error === null) {
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100vh',
          fontFamily: 'system-ui, sans-serif',
          color: '#888',
        }}
      >
        Loading…
      </div>
    )
  }

  // ── error ──────────────────────────────────────────────────────
  if (error !== null) {
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100vh',
          fontFamily: 'system-ui, sans-serif',
          color: '#d32f2f',
        }}
      >
        Error: {error}
      </div>
    )
  }

  const onOnboardingPage = location.pathname === '/onboarding'

  // Not onboarded and trying to access a protected page → onboarding
  if (!isOnboarded && !onOnboardingPage) {
    return <Navigate to="/onboarding" replace />
  }

  // Already onboarded and on the onboarding page → jobs
  if (isOnboarded && onOnboardingPage) {
    return <Navigate to="/jobs" replace />
  }

  return <Outlet />
}
