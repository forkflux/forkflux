import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { JobListQuery } from '../types/job'

/**
 * jobService data-source resolution tests.
 *
 * Locks the contract that `FE_USE_MOCKS === 'true'` selects the mock data
 * source and any other value (including unset) selects the live API data
 * source. The API is the default.
 */

const defaultQuery = (): JobListQuery => ({
  status: 'all',
  role: 'all',
  search: '',
  sort: 'created_at',
  dir: 'desc',
  limit: 10,
  offset: 0,
})

describe('jobService data-source resolution', () => {
  beforeEach(() => {
    vi.resetModules()
  })

  it('uses mockDataSource when FE_USE_MOCKS is "true"', async () => {
    vi.stubEnv('FE_USE_MOCKS', 'true')
    // Ensure the API base URL is unset so that if the mock were not selected,
    // the API source would throw — proving the mock is actually in use.
    vi.stubEnv('FE_API_BASE_URL', '')

    const { jobService } = await import('./jobService')

    // mockDataSource.fetchJobs resolves synchronously with a page object.
    await expect(jobService.fetchJobs(defaultQuery())).resolves.toBeDefined()
  })

  it('uses apiDataSource when FE_USE_MOCKS is unset', async () => {
    vi.stubEnv('FE_USE_MOCKS', '')
    vi.stubEnv('FE_API_BASE_URL', '')

    const fetchSpy = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ items: [], total: 0, limit: 10, offset: 0 }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchSpy)

    const { jobService } = await import('./jobService')

    await jobService.fetchJobs(defaultQuery())

    expect(fetchSpy).toHaveBeenCalledTimes(1)
    const [url] = fetchSpy.mock.calls[0] as [string, RequestInit]
    expect(url).toContain('/api/v1/ui/jobs')

    vi.unstubAllGlobals()
  })

  it('uses apiDataSource when FE_USE_MOCKS is "false"', async () => {
    vi.stubEnv('FE_USE_MOCKS', 'false')
    vi.stubEnv('FE_API_BASE_URL', '')

    const fetchSpy = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ items: [], total: 0, limit: 10, offset: 0 }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchSpy)

    const { jobService } = await import('./jobService')

    await jobService.fetchJobs(defaultQuery())

    expect(fetchSpy).toHaveBeenCalledTimes(1)
    const [url] = fetchSpy.mock.calls[0] as [string, RequestInit]
    expect(url).toContain('/api/v1/ui/jobs')

    vi.unstubAllGlobals()
  })
})
