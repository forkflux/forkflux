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
  },
}))

vi.mock('./services/jobService', () => ({
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
})
