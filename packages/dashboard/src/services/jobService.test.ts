import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { JobListQuery } from '../types/job'

/**
 * Separate job-service entry-point tests.
 *
 * Runtime environment selection belongs to Vite's alias configuration. These
 * tests verify that the production and mocked entry points expose the intended
 * data sources independently.
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

describe('jobService entry points', () => {
  beforeEach(() => {
    vi.unstubAllEnvs()
    vi.unstubAllGlobals()
  })

  it('uses the mocked source from the mocked entry point', async () => {
    const { jobService } = await import('./jobService.mock')
    await expect(jobService.fetchJobs(defaultQuery())).resolves.toBeDefined()
  })

  it('uses the API source from the production entry point', async () => {
    vi.stubEnv('FE_API_BASE_URL', '')

    const fetchSpy = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ items: [], total: 0, limit: 10, offset: 0 }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchSpy)

    const { jobService } = await import('./jobService.api')

    await jobService.fetchJobs(defaultQuery())

    expect(fetchSpy).toHaveBeenCalledTimes(1)
    const [url] = fetchSpy.mock.calls[0] as [string, RequestInit]
    expect(url).toContain('/api/v1/ui/jobs')

    vi.unstubAllGlobals()
  })

})
