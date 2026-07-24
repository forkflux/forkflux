import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { JobListQuery } from '../types/job'

// ---------------------------------------------------------------------------
// Mock setup
// ---------------------------------------------------------------------------

// Mock the dynamic import for detail JSON so we can control the detail data
// without relying on the actual mocks/details/7.json file.
const mockDetail = {
  id: 7,
  parent_job_id: null,
  parent_job_summary: null,
  summary: 'Migrate status pills to lifecycle order',
  status: 'blocked',
  priority: 20,
  source_agent_label: 'source-agent',
  assignee_agent_label: 'assignee-agent',
  target_role_label: 'Frontend Engineer',
  context_payload: {},
  constraints: [],
  artifacts: [],
  failure_reason: null,
  blocked_reason: 'Waiting on upstream dependency',
  unblock_reason: null,
  published_at: '2026-01-01T00:01:00Z',
  claimed_at: '2026-01-01T00:02:00Z',
  started_at: '2026-01-01T00:03:00Z',
  completed_at: null,
  failed_at: null,
  blocked_at: '2026-01-01T00:04:00Z',
  unblocked_at: null,
  cancelled_at: null,
  expires_at: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:04:00Z',
}

// Mock the jobs.json and roles.json static imports
vi.mock('../../mocks/jobs.json', () => ({
  default: [
    {
      id: 7,
      parent_job_id: null,
      parent_job_summary: null,
      summary: 'Migrate status pills to lifecycle order',
      status: 'blocked',
      priority: 20,
      source_agent_label: 'source-agent',
      assignee_agent_label: 'assignee-agent',
      target_role_label: 'Frontend Engineer',
      created_at: '2026-01-01T00:00:00Z',
    },
    {
      id: 8,
      parent_job_id: null,
      parent_job_summary: null,
      summary: 'Another job',
      status: 'published',
      priority: 30,
      source_agent_label: 'source-agent',
      assignee_agent_label: null,
      target_role_label: 'Backend Engineer',
      created_at: '2026-01-02T00:00:00Z',
    },
  ],
}))

vi.mock('../../mocks/roles.json', () => ({
  default: [
    {
      id: 1,
      role_key: 'frontend',
      role_label: 'Frontend Engineer',
      created_at: '2026-07-16T10:00:00Z',
    },
  ],
}))

// Mock the dynamic import for detail files
vi.mock('../../mocks/details/7.json', () => ({
  default: mockDetail,
}))

// Import after mocks are set up
const { mockDataSource, __resetMockState } = await import('./mockDataSource')

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function defaultQuery(overrides: Partial<JobListQuery> = {}): JobListQuery {
  return {
    status: 'all',
    role: 'all',
    search: '',
    sort: 'created_at',
    dir: 'desc',
    limit: 50,
    offset: 0,
    ...overrides,
  }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('mockDataSource', () => {
  beforeEach(() => {
    __resetMockState()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('unblockJob', () => {
    it('returns UnblockJobResponse with correct fields on success', async () => {
      const result = await mockDataSource.unblockJob(7, 'Dependency resolved')

      expect(result).toEqual({
        job_id: 7,
        previous_status: 'blocked',
        new_status: 'unblocked',
        unblock_reason: 'Dependency resolved',
      })
    })

    it('throws "Job not found" for non-existent job ID', async () => {
      await expect(mockDataSource.unblockJob(999, 'Some reason')).rejects.toThrow(
        'Job not found',
      )
    })

    it('throws "cannot be unblocked" when job is not in blocked status', async () => {
      await expect(mockDataSource.unblockJob(8, 'Some reason')).rejects.toThrow(
        'cannot be unblocked',
      )
    })

    it('persists mutation so fetchJobDetail returns unblocked status after unblock', async () => {
      // Before unblock: detail should be blocked
      const before = await mockDataSource.fetchJobDetail(7)
      expect(before).not.toBeNull()
      expect(before!.status).toBe('blocked')
      expect(before!.unblock_reason).toBeNull()
      expect(before!.unblocked_at).toBeNull()

      // Unblock the job
      await mockDataSource.unblockJob(7, 'Dependency resolved by ops')

      // After unblock: detail should reflect the mutation
      const after = await mockDataSource.fetchJobDetail(7)
      expect(after).not.toBeNull()
      expect(after!.status).toBe('unblocked')
      expect(after!.unblock_reason).toBe('Dependency resolved by ops')
      expect(after!.unblocked_at).not.toBeNull()
      expect(after!.blocked_reason).toBeNull()
      expect(after!.blocked_at).toBeNull()
    })

    it('persists mutation so fetchJobs reflects unblocked status after unblock', async () => {
      // Unblock job 7
      await mockDataSource.unblockJob(7, 'Dependency resolved')

      // Fetch jobs — job 7 should now have status 'unblocked'
      const result = await mockDataSource.fetchJobs(defaultQuery())
      const job7 = result.items.find((j) => j.id === 7)
      expect(job7).toBeDefined()
      expect(job7!.status).toBe('unblocked')
    })

    it('persists mutation so fetchJobCounts reflects unblocked count after unblock', async () => {
      // Before unblock: blocked count should be 1, unblocked count should be 0
      const before = await mockDataSource.fetchJobCounts()
      const beforeBlocked = before.find((c) => c.status === 'blocked')
      const beforeUnblocked = before.find((c) => c.status === 'unblocked')
      expect(beforeBlocked?.count).toBe(1)
      expect(beforeUnblocked?.count).toBe(0)

      // Unblock job 7
      await mockDataSource.unblockJob(7, 'Dependency resolved')

      // After unblock: blocked count should be 0, unblocked count should be 1
      const after = await mockDataSource.fetchJobCounts()
      const afterBlocked = after.find((c) => c.status === 'blocked')
      const afterUnblocked = after.find((c) => c.status === 'unblocked')
      expect(afterBlocked?.count).toBe(0)
      expect(afterUnblocked?.count).toBe(1)
    })

    it('throws when trying to unblock an already-unblocked job', async () => {
      // First unblock succeeds
      await mockDataSource.unblockJob(7, 'First unblock')

      // Second unblock should fail — job is now 'unblocked', not 'blocked'
      await expect(mockDataSource.unblockJob(7, 'Second unblock')).rejects.toThrow(
        'cannot be unblocked',
      )
    })
  })
})
