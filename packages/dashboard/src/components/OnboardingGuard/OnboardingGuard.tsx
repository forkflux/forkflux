import { useCallback, useEffect, useState } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { jobService } from '@job-service'

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
 * Exposes a `refreshProfile` callback via Outlet context so the onboarding
 * page can eagerly update the guard's state after setup completes, preventing
 * a redirect back to `/onboarding`.
 */
export function OnboardingGuard() {
  const location = useLocation()
  const [isOnboarded, setIsOnboarded] = useState<boolean | null>(null)
  const [error, setError] = useState<string | null>(null)

  const checkProfile = useCallback(() => {
    jobService
      .getProfile()
      .then((onboarded) => {
        setIsOnboarded(onboarded)
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Failed to check onboarding status')
      })
  }, [])

  useEffect(() => {
    checkProfile()
  }, [checkProfile])

  // ── loading ────────────────────────────────────────────────────
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

  return <Outlet context={{ refreshProfile: checkProfile }} />
}

/** Context shape exposed by OnboardingGuard via `<Outlet context>`. */
export interface OnboardingGuardContext {
  refreshProfile: () => void
}
