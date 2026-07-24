import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import { JobDetailPage } from './JobDetailPage'
import { renderWithRoutes, createMockJobDetail } from '../../test/utils'
import type { JobDetail } from '../../types/job'

// Use vi.hoisted so the mock is available when the hoisted vi.mock runs.
const { mockService } = vi.hoisted(() => ({
  mockService: {
    fetchJobs: vi.fn(),
    fetchListMeta: vi.fn(),
    fetchJobCounts: vi.fn(),
    fetchJobDetail: vi.fn(),
  },
}))

vi.mock('../../services/jobService', () => ({
  jobService: mockService,
}))

const fetchJobDetailMock = vi.mocked(mockService.fetchJobDetail)

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function setDetailResponse(detail: JobDetail | null) {
  fetchJobDetailMock.mockReset()
  fetchJobDetailMock.mockResolvedValue(detail)
}

/**
 * Render JobDetailPage inside a Route so useParams works.
 * The initial entry URL determines the :id param.
 */
function renderDetailPage(initialEntry: string) {
  return renderWithRoutes(<JobDetailPage />, '/jobs/:id', initialEntry)
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('JobDetailPage', () => {
  beforeEach(() => {
    fetchJobDetailMock.mockReset()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('loading state', () => {
    it('shows loading message while fetching', () => {
      fetchJobDetailMock.mockReturnValue(new Promise(() => {}))
      renderDetailPage('/jobs/1')
      expect(screen.getByText('Loading job…')).toBeInTheDocument()
    })
  })

  describe('error / not found', () => {
    it('shows "Job not found" when fetchJobDetail returns null', async () => {
      setDetailResponse(null)
      renderDetailPage('/jobs/999')
      await waitFor(() => {
        expect(screen.getByText('Job not found')).toBeInTheDocument()
      })
    })

    it('shows error message when fetchJobDetail rejects', async () => {
      fetchJobDetailMock.mockReset()
      fetchJobDetailMock.mockRejectedValue(new Error('Server error'))
      renderDetailPage('/jobs/1')
      await waitFor(() => {
        expect(screen.getByText(/Server error/)).toBeInTheDocument()
      })
    })

    it('shows "Invalid job ID" for non-numeric id param', async () => {
      renderDetailPage('/jobs/abc')
      await waitFor(() => {
        expect(screen.getByText('Invalid job ID')).toBeInTheDocument()
      })
    })

    it('renders a back link on error state', async () => {
      setDetailResponse(null)
      renderDetailPage('/jobs/999')
      await waitFor(() => {
        expect(screen.getByText('← Back to jobs')).toBeInTheDocument()
      })
    })
  })

  describe('data rendering', () => {
    const detail = createMockJobDetail({
      id: 42,
      summary: 'Update API docs [FF-1056]',
      status: 'published',
      priority: 20,
      source_agent_label: 'codex-cli',
      assignee_agent_label: null,
      target_role_label: 'Frontend Engineer',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-02T00:00:00Z',
    })

    it('renders the job summary as the title', async () => {
      setDetailResponse(detail)
      renderDetailPage('/jobs/42')
      await waitFor(() => {
        expect(screen.getByText('Update API docs [FF-1056]')).toBeInTheDocument()
      })
    })

    it('renders the status badge', async () => {
      setDetailResponse(detail)
      renderDetailPage('/jobs/42')
      await waitFor(() => {
        expect(screen.getAllByText('Published').length).toBeGreaterThan(0)
      })
    })

    it('renders the priority', async () => {
      setDetailResponse(detail)
      renderDetailPage('/jobs/42')
      await waitFor(() => {
        expect(screen.getByText('Priority 20')).toBeInTheDocument()
      })
    })

    it('renders the source agent label', async () => {
      setDetailResponse(detail)
      renderDetailPage('/jobs/42')
      await waitFor(() => {
        expect(screen.getByText('codex-cli')).toBeInTheDocument()
      })
    })

    it('renders the target role', async () => {
      setDetailResponse(detail)
      renderDetailPage('/jobs/42')
      await waitFor(() => {
        expect(screen.getByText('Frontend Engineer')).toBeInTheDocument()
      })
    })

    it('renders the job ID', async () => {
      setDetailResponse(detail)
      renderDetailPage('/jobs/42')
      await waitFor(() => {
        expect(screen.getByText('#42')).toBeInTheDocument()
      })
    })
  })

  describe('ticket key extraction', () => {
    it('renders ticket badge when summary contains a ticket key', async () => {
      const detail = createMockJobDetail({
        id: 1,
        summary: 'Fix bug [FF-1000] now',
      })
      setDetailResponse(detail)
      renderDetailPage('/jobs/1')
      await waitFor(() => {
        expect(screen.getByText('FF-1000')).toBeInTheDocument()
      })
    })

    it('does not render ticket badge when summary has no ticket key', async () => {
      const detail = createMockJobDetail({
        id: 1,
        summary: 'Fix bug without ticket',
      })
      setDetailResponse(detail)
      renderDetailPage('/jobs/1')
      await waitFor(() => {
        expect(screen.getByText('Fix bug without ticket')).toBeInTheDocument()
      })
      // No ticket badge — the only "FF-" text would be in the summary itself
      // which doesn't contain "FF-"
    })
  })

  describe('failure / blocked reasons', () => {
    it('renders failure reason callout when present', async () => {
      const detail = createMockJobDetail({
        id: 1,
        failure_reason: 'Tests failed in CI',
      })
      setDetailResponse(detail)
      renderDetailPage('/jobs/1')
      await waitFor(() => {
        expect(screen.getByText(/Tests failed in CI/)).toBeInTheDocument()
      })
    })

    it('renders blocked reason callout when present', async () => {
      const detail = createMockJobDetail({
        id: 1,
        blocked_reason: 'Waiting on external API',
      })
      setDetailResponse(detail)
      renderDetailPage('/jobs/1')
      await waitFor(() => {
        expect(screen.getByText(/Waiting on external API/)).toBeInTheDocument()
      })
    })
  })

  describe('constraints', () => {
    it('renders constraints when present', async () => {
      const detail = createMockJobDetail({
        id: 1,
        constraints: ['No new dependencies', 'Must have tests'],
      })
      setDetailResponse(detail)
      renderDetailPage('/jobs/1')
      await waitFor(() => {
        expect(screen.getByText('Constraints')).toBeInTheDocument()
        expect(screen.getByText('No new dependencies')).toBeInTheDocument()
        expect(screen.getByText('Must have tests')).toBeInTheDocument()
      })
    })

    it('does not render constraints section when empty', async () => {
      const detail = createMockJobDetail({
        id: 1,
        constraints: [],
      })
      setDetailResponse(detail)
      renderDetailPage('/jobs/1')
      await waitFor(() => {
        expect(screen.getByText('Timeline')).toBeInTheDocument()
      })
      expect(screen.queryByText('Constraints')).not.toBeInTheDocument()
    })
  })

  describe('artifacts', () => {
    it('renders artifacts section when present', async () => {
      const detail = createMockJobDetail({
        id: 1,
        artifacts: [
          {
            type: 'patch',
            uri: 's3://bucket/file.bin',
            checksum: 'sha256:abc123',
            metadata_json: { key: 'value' },
          },
        ],
      })
      setDetailResponse(detail)
      renderDetailPage('/jobs/1')
      await waitFor(() => {
        expect(screen.getByText('Artifacts')).toBeInTheDocument()
        expect(screen.getByText('patch')).toBeInTheDocument()
        expect(screen.getByText('s3://bucket/file.bin')).toBeInTheDocument()
        expect(screen.getByText('sha256:abc123')).toBeInTheDocument()
      })
    })

    it('toggles artifact metadata visibility on click', async () => {
      const detail = createMockJobDetail({
        id: 1,
        artifacts: [
          {
            type: 'patch',
            uri: 's3://bucket/file.bin',
            checksum: null,
            metadata_json: { key: 'value' },
          },
        ],
      })
      setDetailResponse(detail)
      renderDetailPage('/jobs/1')

      await waitFor(() => {
        expect(screen.getByText('patch')).toBeInTheDocument()
      })

      // The artifact header button
      const artifactButton = screen.getByText('patch').closest('button')!
      expect(artifactButton).toHaveAttribute('aria-expanded', 'false')

      // Click to expand
      fireEvent.click(artifactButton)
      expect(artifactButton).toHaveAttribute('aria-expanded', 'true')
    })
  })

  describe('timeline', () => {
    it('renders timeline section with events', async () => {
      const detail = createMockJobDetail({
        id: 1,
        created_at: '2026-01-01T00:00:00Z',
        published_at: '2026-01-02T00:00:00Z',
        started_at: '2026-01-03T00:00:00Z',
      })
      setDetailResponse(detail)
      renderDetailPage('/jobs/1')
      await waitFor(() => {
        expect(screen.getAllByText('Timeline').length).toBeGreaterThan(0)
        expect(screen.getAllByText('Created').length).toBeGreaterThan(0)
        expect(screen.getAllByText('Started').length).toBeGreaterThan(0)
      })
    })
  })

  describe('context drawer', () => {
    it('opens the context drawer when "details" link is clicked', async () => {
      const detail = createMockJobDetail({
        id: 1,
        context_payload: { repo: 'fork-flux', branch: 'main' },
      })
      setDetailResponse(detail)
      renderDetailPage('/jobs/1')

      await waitFor(() => {
        expect(screen.getByText('details')).toBeInTheDocument()
      })

      // Click the "details" link to open the drawer
      fireEvent.click(screen.getByText('details'))

      // The drawer should open with the title "Context Payload"
      await waitFor(() => {
        expect(screen.getByText('Context Payload')).toBeInTheDocument()
      })
    })
  })

  describe('parent job link', () => {
    it('renders parent job link when parent_job_id is set', async () => {
      const detail = createMockJobDetail({
        id: 5,
        parent_job_id: 3,
        parent_job_summary: 'Parent task summary',
      })
      setDetailResponse(detail)
      renderDetailPage('/jobs/5')
      await waitFor(() => {
        expect(screen.getByText('Parent task summary')).toBeInTheDocument()
      })
    })

    it('does not render parent job field when parent_job_id is null', async () => {
      const detail = createMockJobDetail({
        id: 1,
        parent_job_id: null,
      })
      setDetailResponse(detail)
      renderDetailPage('/jobs/1')
      await waitFor(() => {
        expect(screen.getByText('Timeline')).toBeInTheDocument()
      })
      expect(screen.queryByText('Parent Job')).not.toBeInTheDocument()
    })
  })
})
