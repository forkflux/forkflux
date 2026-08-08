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
  retry_count: 0,
  max_retries: 3,
  context_payload: {},
  constraints: [],
  artifacts: [],
  failure_reason: null,
  blocked_reason: 'Waiting on upstream dependency',
  unblock_reason: null,
  published_at: '2026-01-01T00:01:00Z',
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
      retry_count: 0,
      max_retries: 3,
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
      retry_count: 0,
      max_retries: 3,
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

vi.mock('../../mocks/agents.json', () => ({
  default: [
    {
      id: 1,
      agent_label: 'frontend-bot',
      tool_family: 'playwright',
      created_at: '2026-07-16T10:00:00Z',
      roles: [{ role_key: 'frontend', role_label: 'Frontend Engineer' }],
    },
    {
      id: 2,
      agent_label: 'fullstack-agent',
      tool_family: null,
      created_at: '2026-07-18T09:15:00Z',
      roles: [
        { role_key: 'frontend', role_label: 'Frontend Engineer' },
        { role_key: 'backend', role_label: 'Backend Engineer' },
      ],
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

  // -------------------------------------------------------------------------
  // fetchRoles
  // -------------------------------------------------------------------------

  describe('fetchRoles', () => {
    it('returns all roles from the mock roles JSON', async () => {
      const result = await mockDataSource.fetchRoles()

      expect(result).toHaveLength(1)
      expect(result[0]).toEqual({
        id: 1,
        role_key: 'frontend',
        role_label: 'Frontend Engineer',
        created_at: '2026-07-16T10:00:00Z',
      })
    })

    it('returns consistent data across multiple calls', async () => {
      const first = await mockDataSource.fetchRoles()
      const second = await mockDataSource.fetchRoles()

      expect(first).toEqual(second)
    })
  })

  // -----------------------------------------------------------------------
  // createRole
  // -----------------------------------------------------------------------

  describe('createRole', () => {
    beforeEach(() => {
      __resetMockState()
    })

    afterEach(() => {
      __resetMockState()
    })

    it('creates a role and returns it', async () => {
      const role = await mockDataSource.createRole('qa', 'QA Tester')

      expect(role.role_key).toBe('qa')
      expect(role.role_label).toBe('QA Tester')
      expect(role.id).toBeGreaterThan(0)
      expect(role.created_at).toBeTruthy()
    })

    it('throws a conflict error for a duplicate key in static data', async () => {
      await expect(
        mockDataSource.createRole('frontend', 'Frontend Engineer'),
      ).rejects.toThrow('A role with the key "frontend" already exists.')
    })

    it('throws a conflict error for a duplicate key in the overlay', async () => {
      await mockDataSource.createRole('qa', 'QA Tester')

      await expect(
        mockDataSource.createRole('qa', 'Another QA'),
      ).rejects.toThrow('A role with the key "qa" already exists.')
    })

    it('makes the new role appear in fetchRoles', async () => {
      const before = await mockDataSource.fetchRoles()
      expect(before).toHaveLength(1)

      await mockDataSource.createRole('qa', 'QA Tester')

      const after = await mockDataSource.fetchRoles()
      expect(after).toHaveLength(2)
      expect(after[1]!.role_key).toBe('qa')
      expect(after[1]!.role_label).toBe('QA Tester')
    })

    it('trims whitespace from key and label', async () => {
      const role = await mockDataSource.createRole('  qa  ', '  QA Tester  ')

      expect(role.role_key).toBe('qa')
      expect(role.role_label).toBe('QA Tester')
    })

    it('makes the new role appear in fetchListMeta roles', async () => {
      const before = await mockDataSource.fetchListMeta(defaultQuery())
      expect(before.roles).toHaveLength(1)

      await mockDataSource.createRole('qa', 'QA Tester')

      const after = await mockDataSource.fetchListMeta(defaultQuery())
      expect(after.roles).toHaveLength(2)
      expect(after.roles[1]!.role_key).toBe('qa')
    })
  })

  // -----------------------------------------------------------------------
  // updateRole
  // -----------------------------------------------------------------------

  describe('updateRole', () => {
    beforeEach(() => {
      __resetMockState()
    })

    afterEach(() => {
      __resetMockState()
    })

    it('updates a static role and returns it with the new values', async () => {
      const updated = await mockDataSource.updateRole(1, 'frontend_renamed', 'Frontend Specialist')

      expect(updated.id).toBe(1)
      expect(updated.role_key).toBe('frontend_renamed')
      expect(updated.role_label).toBe('Frontend Specialist')
      expect(updated.created_at).toBeTruthy()
    })

    it('updates an overlay (created) role', async () => {
      // Create a role via createRole so it lives in the overlay.
      const created = await mockDataSource.createRole('qa', 'QA Tester')

      const updated = await mockDataSource.updateRole(created.id, 'qa_lead', 'QA Lead')

      expect(updated.id).toBe(created.id)
      expect(updated.role_key).toBe('qa_lead')
      expect(updated.role_label).toBe('QA Lead')
    })

    it('trims whitespace from key and label', async () => {
      const updated = await mockDataSource.updateRole(1, '  frontend_v2  ', '  Frontend V2  ')

      expect(updated.role_key).toBe('frontend_v2')
      expect(updated.role_label).toBe('Frontend V2')
    })

    it('makes the updated role appear in fetchRoles with the new values', async () => {
      await mockDataSource.updateRole(1, 'frontend_renamed', 'Frontend Specialist')

      const roles = await mockDataSource.fetchRoles()
      expect(roles).toHaveLength(1)
      expect(roles[0]!.id).toBe(1)
      expect(roles[0]!.role_key).toBe('frontend_renamed')
      expect(roles[0]!.role_label).toBe('Frontend Specialist')
    })

    it('does not duplicate the role in fetchRoles after key change', async () => {
      await mockDataSource.updateRole(1, 'frontend_renamed', 'Frontend Specialist')

      const roles = await mockDataSource.fetchRoles()
      expect(roles).toHaveLength(1)
    })

    it('throws when the role id does not exist', async () => {
      await expect(
        mockDataSource.updateRole(999, 'qa', 'QA Tester'),
      ).rejects.toThrow('This role no longer exists. Please refresh and try again.')
    })

    it('throws a conflict error when role_key is taken by another role', async () => {
      await mockDataSource.createRole('backend', 'Backend Engineer')
      // role id 1 (frontend) already exists; now try to rename role 1 to "backend".
      await expect(
        mockDataSource.updateRole(1, 'backend', 'Frontend Engineer'),
      ).rejects.toThrow('A role with the key "backend" already exists.')
    })

    it('allows updating a role to its own current key (no conflict)', async () => {
      const updated = await mockDataSource.updateRole(1, 'frontend', 'Frontend Engineer V2')

      expect(updated.role_key).toBe('frontend')
      expect(updated.role_label).toBe('Frontend Engineer V2')
    })

    it('holds the updated role in a second update of the same role', async () => {
      await mockDataSource.updateRole(1, 'frontend_renamed', 'Frontend V1')
      await mockDataSource.updateRole(1, 'frontend_v2', 'Frontend V2')

      const roles = await mockDataSource.fetchRoles()
      expect(roles).toHaveLength(1)
      expect(roles[0]!.role_key).toBe('frontend_v2')
      expect(roles[0]!.role_label).toBe('Frontend V2')
    })

    it('throws when role_key exceeds 255 characters', async () => {
      await expect(
        mockDataSource.updateRole(1, 'a'.repeat(256), 'Frontend Engineer'),
      ).rejects.toThrow('Role key must be at most 255 characters.')
    })

    it('throws when role_label exceeds 255 characters', async () => {
      await expect(
        mockDataSource.updateRole(1, 'frontend', 'a'.repeat(256)),
      ).rejects.toThrow('Role label must be at most 255 characters.')
    })
  })

  // -----------------------------------------------------------------------
  // deleteRole
  // -----------------------------------------------------------------------

  describe('deleteRole', () => {
    it('removes the role from fetchRoles after deletion', async () => {
      const before = await mockDataSource.fetchRoles()
      expect(before).toHaveLength(1)

      await mockDataSource.deleteRole(1)

      const after = await mockDataSource.fetchRoles()
      expect(after).toHaveLength(0)
    })

    it('resolves void on successful deletion', async () => {
      const result = await mockDataSource.deleteRole(1)
      expect(result).toBeUndefined()
    })

    it('removes the role from fetchListMeta roles after deletion', async () => {
      const before = await mockDataSource.fetchListMeta(defaultQuery())
      expect(before.roles).toHaveLength(1)

      await mockDataSource.deleteRole(1)

      const after = await mockDataSource.fetchListMeta(defaultQuery())
      expect(after.roles).toHaveLength(0)
    })

    it('throws a not-found error for a non-existent role ID', async () => {
      await expect(
        mockDataSource.deleteRole(999),
      ).rejects.toThrow('This role no longer exists. Please refresh and try again.')
    })

    it('throws a not-found error for an already-deleted role', async () => {
      await mockDataSource.deleteRole(1)

      await expect(
        mockDataSource.deleteRole(1),
      ).rejects.toThrow('This role no longer exists. Please refresh and try again.')
    })

    it('deletes a created role from the overlay', async () => {
      const created = await mockDataSource.createRole('qa', 'QA Tester')
      const before = await mockDataSource.fetchRoles()
      expect(before).toHaveLength(2)

      await mockDataSource.deleteRole(created.id)

      const after = await mockDataSource.fetchRoles()
      expect(after).toHaveLength(1)
      expect(after.find((r) => r.id === created.id)).toBeUndefined()
    })
  })

  // -----------------------------------------------------------------------
  // fetchAgents
  // -----------------------------------------------------------------------

  describe('fetchAgents', () => {
    it('returns agents from the mock agents JSON', async () => {
      const agents = await mockDataSource.fetchAgents()

      expect(agents).toHaveLength(2)
      expect(agents[0]!.id).toBe(1)
      expect(agents[0]!.agent_label).toBe('frontend-bot')
      expect(agents[0]!.tool_family).toBe('playwright')
      expect(agents[0]!.roles).toEqual([
        { role_key: 'frontend', role_label: 'Frontend Engineer' },
      ])
    })

    it('returns agents with multiple roles', async () => {
      const agents = await mockDataSource.fetchAgents()

      const fullstack = agents.find((a) => a.agent_label === 'fullstack-agent')
      expect(fullstack).toBeDefined()
      expect(fullstack!.roles).toHaveLength(2)
      expect(fullstack!.roles[0]!.role_key).toBe('frontend')
      expect(fullstack!.roles[1]!.role_key).toBe('backend')
    })
  })

  // -----------------------------------------------------------------------
  // createAgent
  // -----------------------------------------------------------------------

  describe('createAgent', () => {
    beforeEach(() => {
      __resetMockState()
    })

    it('creates an agent and returns a response with an api_token', async () => {
      const result = await mockDataSource.createAgent('new-bot', 'codex', [1])

      expect(result.agent_label).toBe('new-bot')
      expect(result.tool_family).toBe('codex')
      expect(result.target_role_ids).toEqual([1])
      expect(result.api_token).toMatch(/^ff_mock_/)
      expect(result.agent_id).toBeGreaterThan(0)
    })

    it('trims whitespace from agent_label', async () => {
      const result = await mockDataSource.createAgent('  new-bot  ', null, [1])

      expect(result.agent_label).toBe('new-bot')
    })

    it('makes the new agent appear in fetchAgents', async () => {
      const before = await mockDataSource.fetchAgents()
      expect(before).toHaveLength(2)

      await mockDataSource.createAgent('new-bot', 'playwright', [1])

      const after = await mockDataSource.fetchAgents()
      expect(after).toHaveLength(3)
      const created = after.find((a) => a.agent_label === 'new-bot')
      expect(created).toBeDefined()
      expect(created!.tool_family).toBe('playwright')
      expect(created!.roles).toEqual([
        { role_key: 'frontend', role_label: 'Frontend Engineer' },
      ])
    })

    it('throws when a target role ID does not exist', async () => {
      await expect(
        mockDataSource.createAgent('new-bot', null, [999]),
      ).rejects.toThrow('One or more selected roles no longer exist.')
    })

    it('resolves multiple role IDs to role summaries', async () => {
      // Create a second role first so we can select both.
      await mockDataSource.createRole('backend', 'Backend Engineer')

      const result = await mockDataSource.createAgent('multi-bot', null, [1])

      // The created agent should have the frontend role resolved.
      expect(result.target_role_ids).toEqual([1])

      const agents = await mockDataSource.fetchAgents()
      const created = agents.find((a) => a.agent_label === 'multi-bot')
      expect(created!.roles).toEqual([
        { role_key: 'frontend', role_label: 'Frontend Engineer' },
      ])
    })

    it('throws when agent_label exceeds 255 characters', async () => {
      await expect(
        mockDataSource.createAgent('a'.repeat(256), null, [1]),
      ).rejects.toThrow('Agent label must be at most 255 characters.')
    })

    it('throws when tool_family exceeds 255 characters', async () => {
      await expect(
        mockDataSource.createAgent('new-bot', 'a'.repeat(256), [1]),
      ).rejects.toThrow('Tool family must be at most 255 characters.')
    })

    it('throws when target_role_ids is empty', async () => {
      await expect(
        mockDataSource.createAgent('new-bot', null, []),
      ).rejects.toThrow('At least one target role is required.')
    })
  })
})
