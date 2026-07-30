import { describe, expect, it, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { render } from '@testing-library/react'
import App from './App'

// Mock jobService so pages don't make real API calls.
const { mockService } = vi.hoisted(() => ({
  mockService: {
    fetchJobs: vi.fn().mockResolvedValue({ items: [], total: 0, limit: 50, offset: 0 }),
    fetchListMeta: vi.fn().mockResolvedValue({ statuses: [], roles: [] }),
    fetchJobCounts: vi.fn().mockResolvedValue([{ status: 'all', count: 0 }]),
    fetchJobDetail: vi.fn().mockResolvedValue(null),
    fetchRoles: vi.fn().mockResolvedValue([]),
    fetchAgents: vi.fn().mockResolvedValue([]),
    getProfile: vi.fn().mockResolvedValue(true),
  },
}))

vi.mock('@job-service', () => ({
  jobService: mockService,
}))

// App uses BrowserRouter internally, so we can't wrap it in MemoryRouter.
// Instead, we use window.history to set the URL before rendering.
function renderAt(path: string) {
  window.history.replaceState({}, '', path)
  return render(<App />)
}

describe('App routing', () => {
  it('redirects from "/" to "/jobs"', async () => {
    renderAt('/')
    await waitFor(() => {
      expect(screen.getByText('Jobs')).toBeInTheDocument()
    })
  })

  it('renders JobListPage at "/jobs"', async () => {
    renderAt('/jobs')
    await waitFor(() => {
      expect(screen.getByText('Jobs')).toBeInTheDocument()
    })
  })

  it('renders JobDetailPage at "/jobs/:id"', async () => {
    renderAt('/jobs/42')
    await waitFor(() => {
      expect(
        screen.getByText(/Loading job|Job not found|Back to jobs/i),
      ).toBeInTheDocument()
    })
  })

  it('renders NotFoundPage for unknown routes', async () => {
    renderAt('/unknown-route')
    await waitFor(() => {
      expect(screen.getByText('404')).toBeInTheDocument()
    })
  })

  it('renders RolesPage at "/roles"', async () => {
    renderAt('/roles')
    await waitFor(() => {
      // Assert page-specific content, not the header "Roles" nav link
      expect(
        screen.getByText(/Loading roles|No roles have been created yet/),
      ).toBeInTheDocument()
    })
  })

  it('renders AgentsPage at "/agents"', async () => {
    renderAt('/agents')
    await waitFor(() => {
      // Assert page-specific content, not the header "Agents" nav link
      expect(
        screen.getByText(/Loading agents|No agents have been registered yet/),
      ).toBeInTheDocument()
    })
  })

  it('redirects to /onboarding when profile returns is_onboarded=false', async () => {
    vi.mocked(mockService.getProfile).mockResolvedValue(false)
    renderAt('/jobs')
    await waitFor(() => {
      expect(
        screen.getByText('Welcome to ForkFlux'),
      ).toBeInTheDocument()
    })
  })

  it('redirects from /onboarding to /jobs when already onboarded', async () => {
    vi.mocked(mockService.getProfile).mockResolvedValue(true)
    renderAt('/onboarding')
    await waitFor(() => {
      expect(screen.getByText('Jobs')).toBeInTheDocument()
    })
  })

  it('reaches /jobs after setup completes without redirecting back to /onboarding', async () => {
    // Start as non-onboarded user visiting a protected page.
    vi.mocked(mockService.getProfile).mockResolvedValue(false)
    renderAt('/jobs')
    await waitFor(() => {
      expect(screen.getByText('Welcome to ForkFlux')).toBeInTheDocument()
    })

    // Simulate setup completion: profile now returns onboarded=true.
    vi.mocked(mockService.getProfile).mockResolvedValue(true)

    // Navigate to /jobs — as handleFinishSetup does after createProfile + refreshProfile.
    renderAt('/jobs')

    await waitFor(() => {
      expect(screen.getByText('Jobs')).toBeInTheDocument()
    })
  })
})
