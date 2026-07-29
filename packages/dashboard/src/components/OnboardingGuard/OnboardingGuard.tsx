import { useEffect, useState } from 'react'
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
 */
export function OnboardingGuard() {
  const location = useLocation()
  const [isOnboarded, setIsOnboarded] = useState<boolean | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    jobService
      .getProfile()
      .then((onboarded) => {
        if (cancelled) return
        setIsOnboarded(onboarded)
      })
      .catch((err) => {
        if (cancelled) return
        setError(err instanceof Error ? err.message : 'Failed to check onboarding status')
      })
    return () => {
      cancelled = true
    }
  }, [])

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

  return <Outlet />
}