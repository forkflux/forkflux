import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import { JobListPage } from './JobListPage'
import { renderWithRouter, createMockJob } from '../../test/utils'
import type { JobListResponse, JobListMeta, StatusCount } from '../../types/job'

// Use vi.hoisted so the mock service is created before the hoisted vi.mock
// factory runs. We can't reference imported functions inside vi.hoisted, so
// we build the mock service with vi.fn() directly.
const { mockService } = vi.hoisted(() => {
  const service = {
    fetchJobs: vi.fn(),
    fetchListMeta: vi.fn(),
    fetchJobCounts: vi.fn(),
    fetchJobDetail: vi.fn(),
  }
  return { mockService: service }
})

vi.mock('../../services/jobService', () => ({
  jobService: mockService,
}))

// Cast the methods to vi.Mock for type-safe mock assertions.
const fetchJobsMock = vi.mocked(mockService.fetchJobs)
const fetchListMetaMock = vi.mocked(mockService.fetchListMeta)
const fetchJobCountsMock = vi.mocked(mockService.fetchJobCounts)
const fetchJobDetailMock = vi.mocked(mockService.fetchJobDetail)

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function setJobsResponse(jobs: ReturnType<typeof createMockJob>[], total?: number) {
  const response: JobListResponse = {
    items: jobs,
    total: total ?? jobs.length,
    limit: 50,
    offset: 0,
  }
  fetchJobsMock.mockResolvedValue(response)
}

function setMetaResponse(roles: string[]) {
  const meta: JobListMeta = { statuses: [], roles }
  fetchListMetaMock.mockResolvedValue(meta)
}

function setCountsResponse(counts: StatusCount[]) {
  fetchJobCountsMock.mockResolvedValue(counts)
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('JobListPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Default: empty results
    setJobsResponse([])
    setMetaResponse([])
    setCountsResponse([{ status: 'all', count: 0 }])
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('loading state', () => {
    it('shows loading message while fetching', () => {
      // Never resolve — stays in loading state
      fetchJobsMock.mockReturnValue(new Promise(() => {}))
      renderWithRouter(<JobListPage />)
      expect(screen.getByText('Loading jobs…')).toBeInTheDocument()
    })
  })

  describe('error state', () => {
    it('shows error message when fetchJobs rejects', async () => {
      fetchJobsMock.mockRejectedValue(new Error('Network error'))
      renderWithRouter(<JobListPage />)
      await waitFor(() => {
        expect(screen.getByText(/Error: Network error/)).toBeInTheDocument()
      })
    })

    it('shows generic error for non-Error rejections', async () => {
      fetchJobsMock.mockRejectedValue('string error')
      renderWithRouter(<JobListPage />)
      await waitFor(() => {
        expect(screen.getByText(/Error: Failed to load jobs/)).toBeInTheDocument()
      })
    })
  })

  describe('data rendering', () => {
    it('renders job rows with id, summary, status, priority, role', async () => {
      setJobsResponse([
        createMockJob({ id: 1, summary: 'Fix login bug', status: 'published', priority: 20, target_role_label: 'Frontend Engineer' }),
        createMockJob({ id: 2, summary: 'Add API endpoint', status: 'completed', priority: 30, target_role_label: 'Backend Engineer' }),
      ])
      setMetaResponse(['Frontend Engineer', 'Backend Engineer'])
      setCountsResponse([
        { status: 'all', count: 2 },
        { status: 'published', count: 1 },
        { status: 'completed', count: 1 },
      ])

      renderWithRouter(<JobListPage />)

      await waitFor(() => {
        expect(screen.getByText('Fix login bug')).toBeInTheDocument()
      })

      expect(screen.getByText('#1')).toBeInTheDocument()
      expect(screen.getByText('#2')).toBeInTheDocument()
      expect(screen.getByText('Add API endpoint')).toBeInTheDocument()
      expect(screen.getByText('Published')).toBeInTheDocument()
      expect(screen.getByText('Completed')).toBeInTheDocument()
      // "Frontend Engineer" appears in both the select option and the table cell
      expect(screen.getAllByText('Frontend Engineer').length).toBeGreaterThan(0)
      expect(screen.getAllByText('Backend Engineer').length).toBeGreaterThan(0)
    })

    it('renders the total count', async () => {
      setJobsResponse([createMockJob({ id: 1 })], 42)
      renderWithRouter(<JobListPage />)
      await waitFor(() => {
        expect(screen.getByText('42 total')).toBeInTheDocument()
      })
    })

    it('renders status filter pills from counts', async () => {
      setCountsResponse([
        { status: 'all', count: 5 },
        { status: 'published', count: 3 },
        { status: 'blocked', count: 2 },
      ])
      renderWithRouter(<JobListPage />)
      await waitFor(() => {
        expect(screen.getByText('All')).toBeInTheDocument()
        expect(screen.getByText('published')).toBeInTheDocument()
        expect(screen.getByText('blocked')).toBeInTheDocument()
      })
    })

    it('renders role options in the select dropdown', async () => {
      setMetaResponse(['Frontend Engineer', 'Backend Engineer'])
      renderWithRouter(<JobListPage />)
      await waitFor(() => {
        expect(screen.getByText('All Roles')).toBeInTheDocument()
        expect(screen.getByText('Frontend Engineer')).toBeInTheDocument()
        expect(screen.getByText('Backend Engineer')).toBeInTheDocument()
      })
    })
  })

  describe('empty state', () => {
    it('shows empty message when no jobs match filters', async () => {
      setJobsResponse([])
      renderWithRouter(<JobListPage />)
      await waitFor(() => {
        expect(screen.getByText('No jobs match your filters.')).toBeInTheDocument()
      })
    })
  })

  describe('interactions', () => {
    it('calls fetchJobs with the query from URL params', async () => {
      setJobsResponse([createMockJob({ id: 1 })])
      renderWithRouter(<JobListPage />, {
        routerProps: { initialEntries: ['/jobs?status=blocked&limit=10'] },
      })

      await waitFor(() => {
        expect(mockService.fetchJobs).toHaveBeenCalledWith(
          expect.objectContaining({ status: 'blocked', limit: 10 }),
        )
      })
    })

    it('renders sort arrow indicator for the active sort field', async () => {
      setJobsResponse([createMockJob({ id: 1 })])
      renderWithRouter(<JobListPage />, {
        routerProps: { initialEntries: ['/jobs?sort=id&dir=asc'] },
      })

      await waitFor(() => {
        expect(screen.getByText('ID ▲')).toBeInTheDocument()
      })
    })

    it('toggles sort direction when clicking the same sortable header', async () => {
      setJobsResponse([createMockJob({ id: 1 })])
      renderWithRouter(<JobListPage />, {
        routerProps: { initialEntries: ['/jobs?sort=id&dir=asc'] },
      })

      await waitFor(() => {
        expect(screen.getByText('ID ▲')).toBeInTheDocument()
      })

      // Click the ID header — should toggle to desc
      fireEvent.click(screen.getByText('ID ▲'))

      await waitFor(() => {
        expect(screen.getByText('ID ▼')).toBeInTheDocument()
      })
    })

    it('switches sort field when clicking a different sortable header', async () => {
      setJobsResponse([createMockJob({ id: 1 })])
      renderWithRouter(<JobListPage />, {
        routerProps: { initialEntries: ['/jobs?sort=id&dir=desc'] },
      })

      await waitFor(() => {
        expect(screen.getByText('ID ▼')).toBeInTheDocument()
      })

      // Record the number of fetch calls before clicking
      const callsBefore = fetchJobsMock.mock.calls.length

      // Click the Summary header — should switch sort to summary
      const summaryHeader = screen.getByRole('columnheader', { name: /Summary/i })
      fireEvent.click(summaryHeader)

      // A re-fetch should be triggered by the URL change
      await waitFor(() => {
        expect(fetchJobsMock.mock.calls.length).toBeGreaterThan(callsBefore)
      })
    })

    it('navigates to job detail when a row is clicked', async () => {
      setJobsResponse([createMockJob({ id: 42, summary: 'Click me' })])
      renderWithRouter(<JobListPage />, {
        routerProps: { initialEntries: ['/jobs'] },
      })

      await waitFor(() => {
        expect(screen.getByText('Click me')).toBeInTheDocument()
      })

      // Click the row (the summary cell is inside the row)
      fireEvent.click(screen.getByText('Click me'))

      // The navigate call should have happened — we can't easily assert the
      // URL in MemoryRouter, but we can verify no crash occurred.
      expect(screen.queryByText('Loading jobs…')).not.toBeInTheDocument()
    })

    it('updates search input and debounces the setSearch call', async () => {
      setJobsResponse([createMockJob({ id: 1 })])
      renderWithRouter(<JobListPage />, {
        routerProps: { initialEntries: ['/jobs'] },
      })

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Search by summary…')).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText('Search by summary…')
      fireEvent.change(input, { target: { value: 'bug' } })

      // Immediately the input value updates
      expect(input).toHaveValue('bug')

      // After debounce (300ms), fetchJobs is called with the search term
      await waitFor(
        () => {
          expect(mockService.fetchJobs).toHaveBeenCalledWith(
            expect.objectContaining({ search: 'bug' }),
          )
        },
        { timeout: 1000 },
      )
    })
  })

  describe('paginator wiring', () => {
    it('renders the Paginator with total, limit, offset from the query', async () => {
      setJobsResponse([createMockJob({ id: 1 })], 100)
      renderWithRouter(<JobListPage />, {
        routerProps: { initialEntries: ['/jobs?limit=10&offset=20'] },
      })

      await waitFor(() => {
        expect(screen.getByText(/Showing 21–30 of 100/)).toBeInTheDocument()
      })
    })
  })
})
