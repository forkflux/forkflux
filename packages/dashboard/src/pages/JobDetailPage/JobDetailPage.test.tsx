import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import { JobDetailPage } from './JobDetailPage'
import { renderWithRoutes, createMockJobDetail } from '../../test/utils'
import type { JobDetail } from '../../types/job'
import '@testing-library/jest-dom/vitest'

// Use vi.hoisted so the mock is available when the hoisted vi.mock runs.
const { mockService } = vi.hoisted(() => ({
  mockService: {
    fetchJobs: vi.fn(),
    fetchListMeta: vi.fn(),
    fetchJobCounts: vi.fn(),
    fetchJobDetail: vi.fn(),
    unblockJob: vi.fn(),
  },
}))

vi.mock('@job-service', () => ({
  jobService: mockService,
}))

const fetchJobDetailMock = vi.mocked(mockService.fetchJobDetail)
const unblockJobMock = vi.mocked(mockService.unblockJob)

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
    unblockJobMock.mockReset()
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

    it('renders upstream and downstream dependencies with links and metadata', async () => {
      setDetailResponse(
        createMockJobDetail({
          id: 42,
          upstream_dependencies: [
            {
              job_id: 7,
              summary: 'Upstream task',
              status: 'completed',
              target_role_label: 'Backend Engineer',
              dependency_type: 'blocks',
            },
          ],
          downstream_dependencies: [
            {
              job_id: 8,
              summary: 'Downstream task',
              status: 'pending',
              target_role_label: 'QA Engineer',
              dependency_type: 'reopen_of',
            },
          ],
        }),
      )
      renderDetailPage('/jobs/42')

      await waitFor(() => {
        expect(screen.getByText('Upstream dependencies')).toBeInTheDocument()
        expect(screen.getByText('Downstream dependencies')).toBeInTheDocument()
      })
      expect(screen.getByRole('link', { name: /#7 Upstream task/ })).toHaveAttribute(
        'href',
        '/jobs/7',
      )
      expect(screen.getByRole('link', { name: /#8 Downstream task/ })).toHaveAttribute(
        'href',
        '/jobs/8',
      )
      // Status badges render as separate elements, so check for the
      // human-readable dependency-type labels and status badge text
      // using regex matchers since the text is split across elements.
      expect(screen.getByText(/Blocks/)).toBeInTheDocument()
      expect(screen.getByText(/Reopen of/)).toBeInTheDocument()
      expect(screen.getByText(/Completed/)).toBeInTheDocument()
      expect(screen.getByText(/Pending/)).toBeInTheDocument()
    })

    it('renders an empty dependency state when no dependencies exist', async () => {
      setDetailResponse(createMockJobDetail({ id: 42 }))
      renderDetailPage('/jobs/42')

      await waitFor(() => {
        expect(screen.getByText('No related dependencies.')).toBeInTheDocument()
      })
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
        expect(screen.getByText('Events')).toBeInTheDocument()
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
            id: 1,
            artifact_type: 'patch',
            artifact_uri: 's3://bucket/file.bin',
            artifact_checksum: 'sha256:abc123',
            metadata_json: { key: 'value' },
            created_at: '2026-01-01T00:00:00Z',
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
            id: 1,
            artifact_type: 'patch',
            artifact_uri: 's3://bucket/file.bin',
            artifact_checksum: null,
            metadata_json: { key: 'value' },
            created_at: '2026-01-01T00:00:00Z',
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

  describe('events', () => {
    it('renders events section with event cards', async () => {
      const detail = createMockJobDetail({
        id: 1,
        events: [
          {
            event_type: 'task_published',
            current_status: 'published',
            actor_agent_label: 'claude-code',
            payload_json: { priority: 20 },
            created_at: '2026-01-01T00:00:00Z',
          },
          {
            event_type: 'task_started',
            current_status: 'in_progress',
            actor_agent_label: 'codex-cli',
            payload_json: { timestamp: '2026-01-02T00:00:00Z' },
            created_at: '2026-01-02T00:00:00Z',
          },
        ],
      })
      setDetailResponse(detail)
      renderDetailPage('/jobs/1')
      await waitFor(() => {
        expect(screen.getByText('Events')).toBeInTheDocument()
        expect(screen.getAllByText('Published').length).toBeGreaterThan(0)
        expect(screen.getAllByText('Started').length).toBeGreaterThan(0)
      })
    })

    it('shows empty state when no events exist', async () => {
      const detail = createMockJobDetail({
        id: 1,
        events: [],
      })
      setDetailResponse(detail)
      renderDetailPage('/jobs/1')
      await waitFor(() => {
        expect(screen.getByText('No events recorded.')).toBeInTheDocument()
      })
    })

    it('toggles event payload visibility on click', async () => {
      const detail = createMockJobDetail({
        id: 1,
        events: [
          {
            event_type: 'task_published',
            current_status: 'published',
            actor_agent_label: 'claude-code',
            payload_json: { priority: 20, target_role_id: 1 },
            created_at: '2026-01-01T00:00:00Z',
          },
        ],
      })
      setDetailResponse(detail)
      renderDetailPage('/jobs/1')

      await waitFor(() => {
        expect(screen.getAllByText('Published').length).toBeGreaterThan(0)
      })

      // The event-type span is inside the button; find it by its class
      const eventTypeSpan = document.querySelector('.ff-detail__event-type')!
      const eventButton = eventTypeSpan.closest('button')!
      expect(eventButton).toHaveAttribute('aria-expanded', 'false')

      fireEvent.click(eventButton)
      expect(eventButton).toHaveAttribute('aria-expanded', 'true')
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
        expect(screen.getByText('Events')).toBeInTheDocument()
      })
      expect(screen.queryByText('Parent Job')).not.toBeInTheDocument()
    })
  })

  describe('unblock button', () => {
    it('renders Unblock button when job status is blocked', async () => {
      const detail = createMockJobDetail({
        id: 1,
        status: 'blocked',
        blocked_reason: 'Waiting on dependency',
      })
      setDetailResponse(detail)
      renderDetailPage('/jobs/1')
      await waitFor(() => {
        expect(screen.getByText('Unblock')).toBeInTheDocument()
      })
    })

    it('does not render Unblock button when job status is not blocked', async () => {
      const detail = createMockJobDetail({
        id: 1,
        status: 'in_progress',
      })
      setDetailResponse(detail)
      renderDetailPage('/jobs/1')
      await waitFor(() => {
        expect(screen.getByText('Priority 20')).toBeInTheDocument()
      })
      expect(screen.queryByText('Unblock')).not.toBeInTheDocument()
    })
  })

  describe('unblock form', () => {
    it('opens the unblock drawer when Unblock button is clicked', async () => {
      const detail = createMockJobDetail({
        id: 1,
        status: 'blocked',
        blocked_reason: 'Waiting on dependency',
      })
      setDetailResponse(detail)
      renderDetailPage('/jobs/1')

      await waitFor(() => {
        expect(screen.getByText('Unblock')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('Unblock'))

      await waitFor(() => {
        expect(screen.getByText('Unblock Job')).toBeInTheDocument()
      })
    })

    it('shows validation error when submitting with empty reason', async () => {
      const detail = createMockJobDetail({
        id: 1,
        status: 'blocked',
      })
      setDetailResponse(detail)
      renderDetailPage('/jobs/1')

      await waitFor(() => {
        expect(screen.getByText('Unblock')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('Unblock'))

      await waitFor(() => {
        expect(screen.getByText('Unblock Job')).toBeInTheDocument()
      })

      // Submit without entering a reason
      fireEvent.click(screen.getByText('Confirm Unblock'))

      await waitFor(() => {
        expect(screen.getByText('Please provide an unblock reason.')).toBeInTheDocument()
      })
      expect(unblockJobMock).not.toHaveBeenCalled()
    })

    it('calls unblockJob with correct args and refreshes detail on success', async () => {
      const blockedDetail = createMockJobDetail({
        id: 5,
        status: 'blocked',
        blocked_reason: 'Waiting on dependency',
      })
      const unblockedDetail = createMockJobDetail({
        id: 5,
        status: 'unblocked',
        unblock_reason: 'Dependency resolved',
        unblocked_at: '2026-07-24T10:00:00Z',
      })

      // First call returns blocked, second call (after unblock) returns unblocked
      fetchJobDetailMock
        .mockResolvedValueOnce(blockedDetail)
        .mockResolvedValueOnce(unblockedDetail)

      unblockJobMock.mockResolvedValue({
        job_id: 5,
        previous_status: 'blocked',
        new_status: 'unblocked',
        unblock_reason: 'Dependency resolved',
      })

      renderDetailPage('/jobs/5')

      await waitFor(() => {
        expect(screen.getByText('Unblock')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('Unblock'))

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/Dependency resolved/)).toBeInTheDocument()
      })

      const textarea = screen.getByPlaceholderText(/Dependency resolved/)
      fireEvent.change(textarea, { target: { value: 'Dependency resolved' } })

      fireEvent.click(screen.getByText('Confirm Unblock'))

      await waitFor(() => {
        expect(unblockJobMock).toHaveBeenCalledWith(5, 'Dependency resolved')
      })

      // Detail should be refreshed — unblocked status badge should appear
      await waitFor(() => {
        expect(screen.getAllByText('Unblocked').length).toBeGreaterThan(0)
      })
    })

    it('shows error message when unblockJob returns 422 (not blocked)', async () => {
      const detail = createMockJobDetail({
        id: 1,
        status: 'blocked',
      })
      setDetailResponse(detail)

      unblockJobMock.mockRejectedValue(
        new Error('This job cannot be unblocked from its current status.'),
      )

      renderDetailPage('/jobs/1')

      await waitFor(() => {
        expect(screen.getByText('Unblock')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('Unblock'))

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/Dependency resolved/)).toBeInTheDocument()
      })

      const textarea = screen.getByPlaceholderText(/Dependency resolved/)
      fireEvent.change(textarea, { target: { value: 'Some reason' } })

      fireEvent.click(screen.getByText('Confirm Unblock'))

      await waitFor(() => {
        expect(screen.getByText(/cannot be unblocked/)).toBeInTheDocument()
      })
    })

    it('shows error message when unblockJob returns 404 (not found)', async () => {
      const detail = createMockJobDetail({
        id: 1,
        status: 'blocked',
      })
      setDetailResponse(detail)

      unblockJobMock.mockRejectedValue(new Error('Job not found'))

      renderDetailPage('/jobs/1')

      await waitFor(() => {
        expect(screen.getByText('Unblock')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('Unblock'))

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/Dependency resolved/)).toBeInTheDocument()
      })

      const textarea = screen.getByPlaceholderText(/Dependency resolved/)
      fireEvent.change(textarea, { target: { value: 'Some reason' } })

      fireEvent.click(screen.getByText('Confirm Unblock'))

      await waitFor(() => {
        expect(screen.getByText('Job not found')).toBeInTheDocument()
      })
    })
  })

  describe('unblocked status display', () => {
    it('renders unblock reason callout when status is unblocked', async () => {
      const detail = createMockJobDetail({
        id: 1,
        status: 'unblocked',
        unblock_reason: 'Dependency was resolved by ops team',
        unblocked_at: '2026-07-24T10:00:00Z',
      })
      setDetailResponse(detail)
      renderDetailPage('/jobs/1')

      await waitFor(() => {
        expect(screen.getByText(/Dependency was resolved by ops team/)).toBeInTheDocument()
      })
    })

    it('renders Unblocked status badge', async () => {
      const detail = createMockJobDetail({
        id: 1,
        status: 'unblocked',
        unblock_reason: 'Resolved',
        unblocked_at: '2026-07-24T10:00:00Z',
      })
      setDetailResponse(detail)
      renderDetailPage('/jobs/1')

      await waitFor(() => {
        expect(screen.getAllByText('Unblocked').length).toBeGreaterThan(0)
      })
    })

    it('renders Unblocked status badge when status is unblocked', async () => {
      const detail = createMockJobDetail({
        id: 1,
        status: 'unblocked',
        unblock_reason: 'Resolved',
        unblocked_at: '2026-07-24T10:00:00Z',
        blocked_at: '2026-07-23T10:00:00Z',
      })
      setDetailResponse(detail)
      renderDetailPage('/jobs/1')

      await waitFor(() => {
        const allUnblocked = screen.getAllByText('Unblocked')
        expect(allUnblocked.length).toBeGreaterThanOrEqual(1)
      })
    })
  })
})
