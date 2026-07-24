import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { JobListQuery } from '../types/job'

// ---------------------------------------------------------------------------
// Mock setup
// ---------------------------------------------------------------------------

// We must set the env var BEFORE importing the module under test, because
// `apiDataSource.ts` reads `import.meta.env.VITE_API_BASE_URL` at module load.
const API_BASE = 'https://api.test.local'

vi.stubEnv('VITE_API_BASE_URL', API_BASE)

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
    it('returns empty meta (no backend endpoint yet)', async () => {
      const result = await apiDataSource.fetchListMeta(defaultQuery())
      expect(result).toEqual({ statuses: [], roles: [] })
    })

    it('does not call fetch', async () => {
      await apiDataSource.fetchListMeta(defaultQuery())
      expect(fetchMock).not.toHaveBeenCalled()
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
          claimed: 2,
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
      expect(result[0]).toEqual({ status: 'all', count: 21 })
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
})

// ---------------------------------------------------------------------------
// getBaseUrl error (separate describe to control env)
// ---------------------------------------------------------------------------

describe('apiDataSource without VITE_API_BASE_URL', () => {
  it('throws synchronously when VITE_API_BASE_URL is not set', async () => {
    // Reset modules so the env is re-read on import.
    vi.resetModules()
    vi.stubEnv('VITE_API_BASE_URL', '')

    const { apiDataSource: freshDataSource } = await import('./apiDataSource')

    // getBaseUrl() throws synchronously inside fetchJobs before the promise
    // is created, so we assert a synchronous throw rather than a rejection.
    expect(() => freshDataSource.fetchJobs(defaultQuery())).toThrow(
      'VITE_API_BASE_URL is not set',
    )

    // Restore for subsequent tests.
    vi.stubEnv('VITE_API_BASE_URL', API_BASE)
    vi.resetModules()
  })
})
