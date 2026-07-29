import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { JobListQuery } from '../types/job'

// ---------------------------------------------------------------------------
// Mock setup
// ---------------------------------------------------------------------------

// We must set the env var BEFORE importing the module under test, because
// `apiDataSource.ts` reads `import.meta.env.FE_API_BASE_URL` at module load.
const API_BASE = 'https://api.test.local'

vi.stubEnv('FE_API_BASE_URL', API_BASE)

// Mock global fetch.
const fetchMock = vi.fn()
vi.stubGlobal('fetch', fetchMock)

// Import after env + fetch are stubbed.
const { apiDataSource } = await import('./apiDataSource')

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

function jsonResponse(body: unknown, ok = true): Response {
  return {
    ok,
    status: ok ? 200 : 500,
    statusText: ok ? 'OK' : 'Internal Server Error',
    json: () => Promise.resolve(body),
  } as Response
}

function notFoundResponse(): Response {
  return {
    ok: false,
    status: 404,
    statusText: 'Not Found',
    json: () => Promise.resolve({}),
  } as Response
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('apiDataSource', () => {
  beforeEach(() => {
    fetchMock.mockReset()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  // -------------------------------------------------------------------------
  // fetchJobs
  // -------------------------------------------------------------------------

  describe('fetchJobs', () => {
    it('calls the correct URL with default query params', async () => {
      const mockResponse = { items: [], total: 0, limit: 50, offset: 0 }
      fetchMock.mockResolvedValue(jsonResponse(mockResponse))

      await apiDataSource.fetchJobs(defaultQuery())

      expect(fetchMock).toHaveBeenCalledTimes(1)
      const url = fetchMock.mock.calls[0][0] as string
      expect(url).toContain(`${API_BASE}/ui/jobs?`)
      expect(url).toContain('limit=50')
      expect(url).toContain('offset=0')
      expect(url).toContain('order=created_at_desc')
      expect(url).toContain('my_roles_only=false')
      // status=all and role=all should be omitted
      expect(url).not.toContain('status=')
      expect(url).not.toContain('target_role_key=')
    })

    it('includes status param when not "all"', async () => {
      fetchMock.mockResolvedValue(jsonResponse({ items: [], total: 0, limit: 50, offset: 0 }))

      await apiDataSource.fetchJobs(defaultQuery({ status: 'blocked' }))

      const url = fetchMock.mock.calls[0][0] as string
      expect(url).toContain('status=blocked')
    })

    it('includes target_role_key param when role is not "all"', async () => {
      fetchMock.mockResolvedValue(jsonResponse({ items: [], total: 0, limit: 50, offset: 0 }))

      await apiDataSource.fetchJobs(defaultQuery({ role: 'frontend' }))

      const url = fetchMock.mock.calls[0][0] as string
      expect(url).toContain('target_role_key=frontend')
    })

    it('builds order param from sort + dir', async () => {
      fetchMock.mockResolvedValue(jsonResponse({ items: [], total: 0, limit: 50, offset: 0 }))

      await apiDataSource.fetchJobs(defaultQuery({ sort: 'priority', dir: 'asc' }))

      const url = fetchMock.mock.calls[0][0] as string
      expect(url).toContain('order=priority_asc')
    })

    it('parses and returns the JSON response', async () => {
      const mockResponse = {
        items: [{ id: 1, summary: 'Job 1' }],
        total: 1,
        limit: 50,
        offset: 0,
      }
      fetchMock.mockResolvedValue(jsonResponse(mockResponse))

      const result = await apiDataSource.fetchJobs(defaultQuery())

      expect(result).toEqual(mockResponse)
    })

    it('throws on non-ok response', async () => {
      fetchMock.mockResolvedValue(jsonResponse({}, false))

      await expect(apiDataSource.fetchJobs(defaultQuery())).rejects.toThrow(
        'Request failed: 500',
      )
    })
  })

  // -------------------------------------------------------------------------
  // fetchListMeta
  // -------------------------------------------------------------------------

  describe('fetchListMeta', () => {
    it('fetches /ui/agents/roles and returns structured roles', async () => {
      const mockRoles = [
        { id: 1, role_key: 'frontend', role_label: 'Frontend Engineer', created_at: '2026-07-16T10:00:00Z' },
        { id: 2, role_key: 'backend', role_label: 'Backend Engineer', created_at: '2026-07-16T10:00:00Z' },
      ]
      fetchMock.mockResolvedValue(jsonResponse(mockRoles))

      const result = await apiDataSource.fetchListMeta(defaultQuery())

      const url = fetchMock.mock.calls[0][0] as string
      expect(url).toBe(`${API_BASE}/ui/agents/roles`)
      expect(result).toEqual({ statuses: [], roles: mockRoles })
    })

    it('handles empty roles list (HTTP 200 with [])', async () => {
      fetchMock.mockResolvedValue(jsonResponse([]))

      const result = await apiDataSource.fetchListMeta(defaultQuery())

      expect(result).toEqual({ statuses: [], roles: [] })
    })

    it('does not send an Authorization header', async () => {
      fetchMock.mockResolvedValue(jsonResponse([]))

      await apiDataSource.fetchListMeta(defaultQuery())

      const fetchOptions = fetchMock.mock.calls[0][1] as RequestInit | undefined
      const headers = fetchOptions?.headers
      // No headers object at all, or no Authorization header within it
      if (headers) {
        const headerObj = headers instanceof Headers
          ? headers
          : new Headers(headers as HeadersInit)
        expect(headerObj.get('Authorization')).toBeNull()
      }
    })

    it('throws on non-ok response', async () => {
      fetchMock.mockResolvedValue(jsonResponse({}, false))

      await expect(apiDataSource.fetchListMeta(defaultQuery())).rejects.toThrow(
        'Request failed: 500',
      )
    })
  })

  // -------------------------------------------------------------------------
  // fetchJobCounts
  // -------------------------------------------------------------------------

  describe('fetchJobCounts', () => {
    it('fetches /ui/jobs/counts and normalizes via toStatusCounts', async () => {
      const countsResponse = {
        counts: {
          published: 5,
          in_progress: 3,
          blocked: 1,
          completed: 10,
          failed: 0,
          cancelled: 0,
        },
      }
      fetchMock.mockResolvedValue(jsonResponse(countsResponse))

      const result = await apiDataSource.fetchJobCounts()

      const url = fetchMock.mock.calls[0][0] as string
      expect(url).toBe(`${API_BASE}/ui/jobs/counts`)

      // First entry is "all" with the total
      expect(result[0]).toEqual({ status: 'all', count: 19 })
      // Known statuses present in lifecycle order
      expect(result.some((c) => c.status === 'published' && c.count === 5)).toBe(true)
      expect(result.some((c) => c.status === 'completed' && c.count === 10)).toBe(true)
    })

    it('throws on non-ok response', async () => {
      fetchMock.mockResolvedValue(jsonResponse({}, false))

      await expect(apiDataSource.fetchJobCounts()).rejects.toThrow(
        'Request failed: 500',
      )
    })
  })

  // -------------------------------------------------------------------------
  // fetchJobDetail
  // -------------------------------------------------------------------------

  describe('fetchJobDetail', () => {
    it('fetches /ui/jobs/:id and returns the detail', async () => {
      const mockDetail = { id: 42, summary: 'Job 42' }
      fetchMock.mockResolvedValue(jsonResponse(mockDetail))

      const result = await apiDataSource.fetchJobDetail(42)

      const url = fetchMock.mock.calls[0][0] as string
      expect(url).toBe(`${API_BASE}/ui/jobs/42`)
      expect(result).toEqual(mockDetail)
    })

    it('returns null on 404', async () => {
      fetchMock.mockResolvedValue(notFoundResponse())

      const result = await apiDataSource.fetchJobDetail(999)
      expect(result).toBeNull()
    })

    it('rethrows non-404 errors', async () => {
      fetchMock.mockResolvedValue(jsonResponse({}, false))

      await expect(apiDataSource.fetchJobDetail(1)).rejects.toThrow(
        'Request failed: 500',
      )
    })
  })

  // -------------------------------------------------------------------------
  // fetchRoles
  // -------------------------------------------------------------------------

  describe('fetchRoles', () => {
    it('fetches /ui/agents/roles and returns the roles array', async () => {
      const mockRoles = [
        { id: 1, role_key: 'frontend', role_label: 'Frontend Engineer', created_at: '2026-07-16T10:00:00Z' },
        { id: 2, role_key: 'backend', role_label: 'Backend Engineer', created_at: '2026-07-16T10:00:00Z' },
      ]
      fetchMock.mockResolvedValue(jsonResponse(mockRoles))

      const result = await apiDataSource.fetchRoles()

      const url = fetchMock.mock.calls[0][0] as string
      expect(url).toBe(`${API_BASE}/ui/agents/roles`)
      expect(result).toEqual(mockRoles)
    })

    it('handles empty roles list (HTTP 200 with [])', async () => {
      fetchMock.mockResolvedValue(jsonResponse([]))

      const result = await apiDataSource.fetchRoles()

      expect(result).toEqual([])
    })

    it('does not send an Authorization header', async () => {
      fetchMock.mockResolvedValue(jsonResponse([]))

      await apiDataSource.fetchRoles()

      const fetchOptions = fetchMock.mock.calls[0][1] as RequestInit | undefined
      const headers = fetchOptions?.headers
      if (headers) {
        const headerObj = headers instanceof Headers
          ? headers
          : new Headers(headers as HeadersInit)
        expect(headerObj.get('Authorization')).toBeNull()
      }
    })

    it('throws on non-ok response', async () => {
      fetchMock.mockResolvedValue(jsonResponse({}, false))

      await expect(apiDataSource.fetchRoles()).rejects.toThrow(
        'Request failed: 500',
      )
    })
  })

  // -------------------------------------------------------------------------
  // unblockJob
  // -------------------------------------------------------------------------

  describe('unblockJob', () => {
    it('calls POST /ui/jobs/:id/unblock with correct URL, method, and body', async () => {
      const mockResponse = {
        job_id: 42,
        previous_status: 'blocked',
        new_status: 'unblocked',
        unblock_reason: 'Dependency resolved',
      }
      fetchMock.mockResolvedValue(jsonResponse(mockResponse))

      await apiDataSource.unblockJob(42, 'Dependency resolved')

      expect(fetchMock).toHaveBeenCalledTimes(1)
      const [url, options] = fetchMock.mock.calls[0] as [string, RequestInit]
      expect(url).toBe(`${API_BASE}/ui/jobs/42/unblock`)
      expect(options.method).toBe('POST')
      expect(options.headers).toEqual({ 'Content-Type': 'application/json' })
      expect(JSON.parse(options.body as string)).toEqual({
        unblock_reason: 'Dependency resolved',
      })
    })

    it('parses and returns the UnblockJobResponse on success', async () => {
      const mockResponse = {
        job_id: 10,
        previous_status: 'blocked',
        new_status: 'unblocked',
        unblock_reason: 'Ops resolved the blocker',
      }
      fetchMock.mockResolvedValue(jsonResponse(mockResponse))

      const result = await apiDataSource.unblockJob(10, 'Ops resolved the blocker')

      expect(result).toEqual(mockResponse)
    })

    it('throws "Job not found" on 404', async () => {
      fetchMock.mockResolvedValue(notFoundResponse())

      await expect(apiDataSource.unblockJob(999, 'Some reason')).rejects.toThrow(
        'Job not found',
      )
    })

    it('throws "cannot be unblocked" on 422', async () => {
      const unprocessableResponse = {
        ok: false,
        status: 422,
        statusText: 'Unprocessable Content',
        json: () => Promise.resolve({}),
      } as Response
      fetchMock.mockResolvedValue(unprocessableResponse)

      await expect(apiDataSource.unblockJob(1, 'Some reason')).rejects.toThrow(
        'cannot be unblocked',
      )
    })

    it('throws generic error on other non-ok status', async () => {
      fetchMock.mockResolvedValue(jsonResponse({}, false))

      await expect(apiDataSource.unblockJob(1, 'Some reason')).rejects.toThrow(
        'Request failed: 500',
      )
    })
  })
})

// ---------------------------------------------------------------------------
// getBaseUrl default (separate describe to control env)
// ---------------------------------------------------------------------------

describe('apiDataSource without FE_API_BASE_URL', () => {
  it('defaults to /api/v1 when FE_API_BASE_URL is not set', async () => {
    // Reset modules so the env is re-read on import.
    vi.resetModules()
    vi.stubEnv('FE_API_BASE_URL', '')

    const { apiDataSource: freshDataSource } = await import('./apiDataSource')

    fetchMock.mockReset()
    fetchMock.mockResolvedValue(jsonResponse({ items: [], total: 0, limit: 10, offset: 0 }))

    await freshDataSource.fetchJobs(defaultQuery())

    // The request URL should use the default /api/v1 base.
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toContain('/api/v1/ui/jobs')

    // Restore for subsequent tests.
    vi.stubEnv('FE_API_BASE_URL', API_BASE)
    vi.resetModules()
  })
})

// -------------------------------------------------------------------------
// createRole
// -------------------------------------------------------------------------

describe('createRole', () => {
  beforeEach(() => {
    fetchMock.mockReset()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('sends POST to the correct endpoint with the right payload', async () => {
    const mockRole = {
      id: 10,
      role_key: 'qa',
      role_label: 'QA Tester',
      created_at: '2026-07-24T10:00:00Z',
    }
    fetchMock.mockResolvedValue(jsonResponse(mockRole))

    const result = await apiDataSource.createRole('qa', 'QA Tester')

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, options] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe(`${API_BASE}/ui/agents/roles`)
    expect(options.method).toBe('POST')
    expect(options.headers).toEqual({ 'Content-Type': 'application/json' })
    expect(JSON.parse(options.body as string)).toEqual({
      role_key: 'qa',
      role_label: 'QA Tester',
    })
    expect(result).toEqual(mockRole)
  })

  it('throws a conflict error on 422 with target_role.conflict code', async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 422,
      statusText: 'Unprocessable Entity',
      json: () => Promise.resolve({
        detail: [
          {
            loc: ['body', 'role_key'],
            msg: 'Target role already exists.',
            type: 'target_role.conflict',
            input: 'frontend',
            ctx: {},
          },
        ],
      }),
    } as Response)

    await expect(
      apiDataSource.createRole('frontend', 'Frontend Engineer'),
    ).rejects.toThrow('A role with the key "frontend" already exists.')
  })

  it('throws the backend message on non-conflict 422 (validation error)', async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 422,
      statusText: 'Unprocessable Entity',
      json: () => Promise.resolve({
        detail: [
          {
            loc: ['body', 'role_key'],
            msg: 'String should have at most 255 characters',
            type: 'string_too_long',
            input: 'a'.repeat(300),
            ctx: {},
          },
        ],
      }),
    } as Response)

    await expect(
      apiDataSource.createRole('short', 'QA Tester'),
    ).rejects.toThrow('String should have at most 255 characters')
  })

  it('throws a fallback message on 422 with unparseable body', async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 422,
      statusText: 'Unprocessable Entity',
      json: () => Promise.reject(new Error('not JSON')),
    } as Response)

    await expect(
      apiDataSource.createRole('qa', 'QA Tester'),
    ).rejects.toThrow('Invalid input. Please check your values.')
  })

  it('throws client-side error when role_key exceeds 255 chars', async () => {
    const longKey = 'a'.repeat(256)

    await expect(
      apiDataSource.createRole(longKey, 'QA Tester'),
    ).rejects.toThrow('Role key must be at most 255 characters.')

    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('throws client-side error when role_label exceeds 255 chars', async () => {
    const longLabel = 'a'.repeat(256)

    await expect(
      apiDataSource.createRole('qa', longLabel),
    ).rejects.toThrow('Role label must be at most 255 characters.')

    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('throws a generic error on other non-ok status', async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      json: () => Promise.resolve({}),
    } as Response)

    await expect(
      apiDataSource.createRole('qa', 'QA Tester'),
    ).rejects.toThrow('Request failed: 500 Internal Server Error')
  })

  // -----------------------------------------------------------------------
  // fetchAgents
  // -----------------------------------------------------------------------

  describe('fetchAgents', () => {
    it('calls the correct URL', async () => {
      const mockAgents = [
        {
          id: 1,
          agent_label: 'frontend-bot',
          tool_family: 'playwright',
          created_at: '2026-07-16T10:00:00Z',
          roles: [{ role_key: 'frontend', role_label: 'Frontend Engineer' }],
        },
      ]
      fetchMock.mockResolvedValue(jsonResponse(mockAgents))

      const result = await apiDataSource.fetchAgents()

      expect(fetchMock).toHaveBeenCalledTimes(1)
      expect(fetchMock.mock.calls[0][0]).toBe(`${API_BASE}/ui/agents`)
      expect(result).toEqual(mockAgents)
    })

    it('returns an empty array when no agents exist', async () => {
      fetchMock.mockResolvedValue(jsonResponse([]))

      const result = await apiDataSource.fetchAgents()

      expect(result).toEqual([])
    })

    it('throws on non-ok response', async () => {
      fetchMock.mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: () => Promise.resolve({}),
      } as Response)

      await expect(apiDataSource.fetchAgents()).rejects.toThrow(
        'Request failed: 500 Internal Server Error',
      )
    })
  })

  // -------------------------------------------------------------------------
  // createAgent
  // -------------------------------------------------------------------------

  describe('createAgent', () => {
    beforeEach(() => {
      fetchMock.mockReset()
    })

    afterEach(() => {
      vi.restoreAllMocks()
    })

    it('sends POST to the correct endpoint with the right payload', async () => {
      const mockResponse = {
        agent_id: 10,
        agent_label: 'my-bot',
        tool_family: 'playwright',
        target_role_ids: [1, 2],
        api_token: 'ff_secret_token',
      }
      fetchMock.mockResolvedValue({
        ok: true,
        status: 201,
        statusText: 'Created',
        json: () => Promise.resolve(mockResponse),
      } as Response)

      const result = await apiDataSource.createAgent('my-bot', 'playwright', [1, 2])

      expect(fetchMock).toHaveBeenCalledTimes(1)
      const [url, options] = fetchMock.mock.calls[0] as [string, RequestInit]
      expect(url).toBe(`${API_BASE}/ui/agents`)
      expect(options.method).toBe('POST')
      expect(options.headers).toEqual({ 'Content-Type': 'application/json' })
      expect(JSON.parse(options.body as string)).toEqual({
        agent_label: 'my-bot',
        tool_family: 'playwright',
        target_role_ids: [1, 2],
      })
      expect(result).toEqual(mockResponse)
      expect(result.api_token).toBe('ff_secret_token')
    })

    it('sends null tool_family when not provided', async () => {
      const mockResponse = {
        agent_id: 11,
        agent_label: 'my-bot',
        tool_family: null,
        target_role_ids: [1],
        api_token: 'ff_token',
      }
      fetchMock.mockResolvedValue({
        ok: true,
        status: 201,
        statusText: 'Created',
        json: () => Promise.resolve(mockResponse),
      } as Response)

      await apiDataSource.createAgent('my-bot', null, [1])

      const [, options] = fetchMock.mock.calls[0] as [string, RequestInit]
      expect(JSON.parse(options.body as string).tool_family).toBeNull()
    })

    it('throws a role-not-found error on 422 with target_role.not_found code', async () => {
      fetchMock.mockResolvedValue({
        ok: false,
        status: 422,
        statusText: 'Unprocessable Entity',
        json: () => Promise.resolve({
          detail: [
            {
              loc: ['body', 'target_role_ids'],
              msg: 'Target role not found.',
              type: 'target_role.not_found',
              input: [999],
              ctx: {},
            },
          ],
        }),
      } as Response)

      await expect(
        apiDataSource.createAgent('my-bot', null, [999]),
      ).rejects.toThrow('One or more selected roles no longer exist.')
    })

    it('throws the backend message on non-role-not-found 422 (validation error)', async () => {
      fetchMock.mockResolvedValue({
        ok: false,
        status: 422,
        statusText: 'Unprocessable Entity',
        json: () => Promise.resolve({
          detail: [
            {
              loc: ['body', 'target_role_ids'],
              msg: 'List should have at least 1 item',
              type: 'too_short',
              input: [],
              ctx: {},
            },
          ],
        }),
      } as Response)

      await expect(
        apiDataSource.createAgent('my-bot', null, [1]),
      ).rejects.toThrow('List should have at least 1 item')
    })

    it('throws a fallback message on 422 with unparseable body', async () => {
      fetchMock.mockResolvedValue({
        ok: false,
        status: 422,
        statusText: 'Unprocessable Entity',
        json: () => Promise.reject(new Error('not JSON')),
      } as Response)

      await expect(
        apiDataSource.createAgent('my-bot', null, [1]),
      ).rejects.toThrow('Invalid input. Please check your values.')
    })

    it('throws on non-ok non-422 response', async () => {
      fetchMock.mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: () => Promise.resolve({}),
      } as Response)

      await expect(
        apiDataSource.createAgent('my-bot', null, [1]),
      ).rejects.toThrow('Request failed: 500 Internal Server Error')
    })

    it('validates agent_label length client-side', async () => {
      await expect(
        apiDataSource.createAgent('a'.repeat(256), null, [1]),
      ).rejects.toThrow('Agent label must be at most 255 characters.')
      expect(fetchMock).not.toHaveBeenCalled()
    })

    it('validates tool_family length client-side', async () => {
      await expect(
        apiDataSource.createAgent('my-bot', 'a'.repeat(256), [1]),
      ).rejects.toThrow('Tool family must be at most 255 characters.')
      expect(fetchMock).not.toHaveBeenCalled()
    })
  })
})
