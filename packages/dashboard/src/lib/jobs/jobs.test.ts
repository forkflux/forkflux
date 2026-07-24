import { describe, expect, it } from 'vitest'
import {
  JOB_STATUS_ORDER,
  countJobsByStatus,
  extractTicketKey,
  filterJobs,
  formatAssignee,
  formatBytes,
  formatDate,
  getDistinctRoles,
  getDistinctStatuses,
  getStatusCounts,
  getTimeline,
  sortJobs,
  toStatusCounts,
} from './jobs'
import type { Job, JobDetail } from '../../types/job'

// ---------------------------------------------------------------------------
// Helpers — build minimal Job objects for tests
// ---------------------------------------------------------------------------

function makeJob(overrides: Partial<Job> = {}): Job {
  return {
    id: 1,
    parent_job_id: null,
    parent_job_summary: null,
    summary: 'Test job',
    status: 'published',
    priority: 20,
    source_agent_label: 'source-agent',
    assignee_agent_label: null,
    target_role_label: 'Frontend Engineer',
    created_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

function makeDetail(overrides: Partial<JobDetail> = {}): JobDetail {
  return {
    ...makeJob(overrides),
    context_payload: {},
    constraints: [],
    artifacts: [],
    failure_reason: null,
    blocked_reason: null,
    published_at: null,
    claimed_at: null,
    started_at: null,
    completed_at: null,
    failed_at: null,
    blocked_at: null,
    cancelled_at: null,
    expires_at: null,
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

// ---------------------------------------------------------------------------
// getDistinctStatuses
// ---------------------------------------------------------------------------

describe('getDistinctStatuses', () => {
  it('returns sorted distinct statuses', () => {
    const jobs = [
      makeJob({ status: 'completed' }),
      makeJob({ status: 'published' }),
      makeJob({ status: 'completed' }),
      makeJob({ status: 'blocked' }),
    ]
    expect(getDistinctStatuses(jobs)).toEqual([
      'blocked',
      'completed',
      'published',
    ])
  })

  it('returns empty array for empty input', () => {
    expect(getDistinctStatuses([])).toEqual([])
  })

  it('returns single-element array for one status', () => {
    const jobs = [makeJob({ status: 'failed' }), makeJob({ status: 'failed' })]
    expect(getDistinctStatuses(jobs)).toEqual(['failed'])
  })
})

// ---------------------------------------------------------------------------
// getStatusCounts
// ---------------------------------------------------------------------------

describe('getStatusCounts', () => {
  it('returns "all" total plus per-status counts sorted alphabetically', () => {
    const jobs = [
      makeJob({ status: 'published' }),
      makeJob({ status: 'published' }),
      makeJob({ status: 'completed' }),
    ]
    const counts = getStatusCounts(jobs)
    expect(counts[0]).toEqual({ status: 'all', count: 3 })
    expect(counts).toContainEqual({ status: 'published', count: 2 })
    expect(counts).toContainEqual({ status: 'completed', count: 1 })
    // Sorted alphabetically: all, completed, published
    expect(counts.map((c) => c.status)).toEqual([
      'all',
      'completed',
      'published',
    ])
  })

  it('returns only "all" with count 0 for empty input', () => {
    expect(getStatusCounts([])).toEqual([{ status: 'all', count: 0 }])
  })
})

// ---------------------------------------------------------------------------
// countJobsByStatus
// ---------------------------------------------------------------------------

describe('countJobsByStatus', () => {
  it('initializes all known statuses to 0', () => {
    const counts = countJobsByStatus([])
    for (const status of JOB_STATUS_ORDER) {
      expect(counts[status]).toBe(0)
    }
  })

  it('counts jobs per status correctly', () => {
    const jobs = [
      makeJob({ status: 'published' }),
      makeJob({ status: 'published' }),
      makeJob({ status: 'completed' }),
      makeJob({ status: 'blocked' }),
    ]
    const counts = countJobsByStatus(jobs)
    expect(counts.published).toBe(2)
    expect(counts.completed).toBe(1)
    expect(counts.blocked).toBe(1)
    expect(counts.failed).toBe(0)
    expect(counts.cancelled).toBe(0)
  })
})

// ---------------------------------------------------------------------------
// toStatusCounts
// ---------------------------------------------------------------------------

describe('toStatusCounts', () => {
  it('prepends "all" total and orders known statuses in lifecycle order', () => {
    const counts = toStatusCounts({
      published: 2,
      completed: 1,
      blocked: 0,
    })
    expect(counts[0]).toEqual({ status: 'all', count: 3 })
    // Lifecycle order: published, blocked, completed (skipping missing ones)
    expect(counts.map((c) => c.status)).toEqual([
      'all',
      'published',
      'blocked',
      'completed',
    ])
  })

  it('appends unknown statuses alphabetically after known ones', () => {
    const counts = toStatusCounts({
      published: 1,
      archived: 2,
      draft: 3,
    })
    const statuses = counts.map((c) => c.status) as string[]
    expect(statuses[0]).toBe('all')
    expect(statuses[1]).toBe('published')
    // Unknown statuses sorted alphabetically
    expect(statuses).toContain('archived')
    expect(statuses).toContain('draft')
    expect(statuses.indexOf('archived')).toBeLessThan(statuses.indexOf('draft'))
  })

  it('handles empty dict', () => {
    expect(toStatusCounts({})).toEqual([{ status: 'all', count: 0 }])
  })

  it('includes all 7 statuses when all present', () => {
    const counts = toStatusCounts({
      published: 1,
      claimed: 1,
      in_progress: 1,
      blocked: 1,
      completed: 1,
      failed: 1,
      cancelled: 1,
    })
    expect(counts[0]).toEqual({ status: 'all', count: 7 })
    expect(counts).toHaveLength(8)
  })
})

// ---------------------------------------------------------------------------
// getDistinctRoles
// ---------------------------------------------------------------------------

describe('getDistinctRoles', () => {
  it('returns sorted distinct roles', () => {
    const jobs = [
      makeJob({ target_role_label: 'Backend Engineer' }),
      makeJob({ target_role_label: 'Frontend Engineer' }),
      makeJob({ target_role_label: 'Backend Engineer' }),
    ]
    expect(getDistinctRoles(jobs)).toEqual([
      'Backend Engineer',
      'Frontend Engineer',
    ])
  })

  it('returns empty array for empty input', () => {
    expect(getDistinctRoles([])).toEqual([])
  })

  it('returns single-element array for one role', () => {
    const jobs = [
      makeJob({ target_role_label: 'QA Engineer' }),
      makeJob({ target_role_label: 'QA Engineer' }),
    ]
    expect(getDistinctRoles(jobs)).toEqual(['QA Engineer'])
  })
})

// ---------------------------------------------------------------------------
// filterJobs
// ---------------------------------------------------------------------------

describe('filterJobs', () => {
  const jobs = [
    makeJob({ id: 1, status: 'published', target_role_label: 'Frontend', summary: 'Fix login bug' }),
    makeJob({ id: 2, status: 'completed', target_role_label: 'Backend', summary: 'Add API endpoint' }),
    makeJob({ id: 3, status: 'published', target_role_label: 'Backend', summary: 'Fix race condition' }),
  ]

  it('filters by status', () => {
    const result = filterJobs(jobs, { status: 'published', role: 'all', search: '' })
    expect(result.map((j) => j.id)).toEqual([1, 3])
  })

  it('filters by role', () => {
    const result = filterJobs(jobs, { status: 'all', role: 'Backend', search: '' })
    expect(result.map((j) => j.id)).toEqual([2, 3])
  })

  it('filters by search (case-insensitive, on summary)', () => {
    const result = filterJobs(jobs, { status: 'all', role: 'all', search: 'FIX' })
    expect(result.map((j) => j.id)).toEqual([1, 3])
  })

  it('trims search before matching', () => {
    const result = filterJobs(jobs, { status: 'all', role: 'all', search: '  login  ' })
    expect(result.map((j) => j.id)).toEqual([1])
  })

  it('combines all filters', () => {
    const result = filterJobs(jobs, { status: 'published', role: 'Backend', search: 'race' })
    expect(result.map((j) => j.id)).toEqual([3])
  })

  it('returns all when status and role are "all" and search is empty', () => {
    const result = filterJobs(jobs, { status: 'all', role: 'all', search: '' })
    expect(result).toHaveLength(3)
  })

  it('does not mutate the input array', () => {
    const original = [...jobs]
    filterJobs(jobs, { status: 'published', role: 'all', search: '' })
    expect(jobs).toEqual(original)
  })
})

// ---------------------------------------------------------------------------
// sortJobs
// ---------------------------------------------------------------------------

describe('sortJobs', () => {
  const jobs = [
    makeJob({ id: 3, summary: 'Charlie', status: 'published', priority: 30, created_at: '2026-03-01T00:00:00Z' }),
    makeJob({ id: 1, summary: 'Alpha', status: 'completed', priority: 10, created_at: '2026-01-01T00:00:00Z' }),
    makeJob({ id: 2, summary: 'Bravo', status: 'blocked', priority: 20, created_at: '2026-02-01T00:00:00Z' }),
  ]

  it('sorts by id ascending', () => {
    const result = sortJobs(jobs, 'id', 'asc')
    expect(result.map((j) => j.id)).toEqual([1, 2, 3])
  })

  it('sorts by id descending', () => {
    const result = sortJobs(jobs, 'id', 'desc')
    expect(result.map((j) => j.id)).toEqual([3, 2, 1])
  })

  it('sorts by priority ascending', () => {
    const result = sortJobs(jobs, 'priority', 'asc')
    expect(result.map((j) => j.priority)).toEqual([10, 20, 30])
  })

  it('sorts by priority descending', () => {
    const result = sortJobs(jobs, 'priority', 'desc')
    expect(result.map((j) => j.priority)).toEqual([30, 20, 10])
  })

  it('sorts by summary (string) ascending', () => {
    const result = sortJobs(jobs, 'summary', 'asc')
    expect(result.map((j) => j.summary)).toEqual(['Alpha', 'Bravo', 'Charlie'])
  })

  it('sorts by status (string) descending', () => {
    const result = sortJobs(jobs, 'status', 'desc')
    expect(result.map((j) => j.status)).toEqual(['published', 'completed', 'blocked'])
  })

  it('sorts by created_at ascending', () => {
    const result = sortJobs(jobs, 'created_at', 'asc')
    expect(result.map((j) => j.id)).toEqual([1, 2, 3])
  })

  it('does not mutate the input array', () => {
    const original = [...jobs]
    sortJobs(jobs, 'id', 'asc')
    expect(jobs).toEqual(original)
  })
})

// ---------------------------------------------------------------------------
// formatDate
// ---------------------------------------------------------------------------

describe('formatDate', () => {
  it('formats a valid ISO timestamp', () => {
    const result = formatDate('2026-01-15T10:30:00Z')
    // The exact output depends on the runtime locale/timezone, but it should
    // contain the year and not be the em-dash fallback.
    expect(result).toContain('2026')
    expect(result).not.toBe('—')
  })

  it('returns em-dash for null', () => {
    expect(formatDate(null)).toBe('—')
  })

  it('returns the original string for an invalid date', () => {
    expect(formatDate('not-a-date')).toBe('not-a-date')
  })
})

// ---------------------------------------------------------------------------
// formatAssignee
// ---------------------------------------------------------------------------

describe('formatAssignee', () => {
  it('returns the label when non-null', () => {
    expect(formatAssignee('agent-42')).toBe('agent-42')
  })

  it('returns em-dash for null', () => {
    expect(formatAssignee(null)).toBe('—')
  })
})

// ---------------------------------------------------------------------------
// formatBytes
// ---------------------------------------------------------------------------

describe('formatBytes', () => {
  it('returns "0 B" for zero', () => {
    expect(formatBytes(0)).toBe('0 B')
  })

  it('formats bytes below 1 KB', () => {
    expect(formatBytes(512)).toBe('512 B')
  })

  it('formats kilobytes', () => {
    expect(formatBytes(1024)).toBe('1.0 KB')
  })

  it('formats megabytes', () => {
    expect(formatBytes(1024 * 1024)).toBe('1.0 MB')
  })

  it('formats gigabytes', () => {
    expect(formatBytes(1024 * 1024 * 1024)).toBe('1.0 GB')
  })

  it('uses 0 decimal places for values >= 100', () => {
    expect(formatBytes(100 * 1024)).toBe('100 KB')
  })
})

// ---------------------------------------------------------------------------
// extractTicketKey
// ---------------------------------------------------------------------------

describe('extractTicketKey', () => {
  it('extracts a ticket key in brackets', () => {
    expect(extractTicketKey('Fix bug [FF-1000] now')).toBe('FF-1000')
  })

  it('returns null when no ticket key is found', () => {
    expect(extractTicketKey('No ticket here')).toBeNull()
  })

  it('returns the first match when multiple brackets exist', () => {
    expect(extractTicketKey('[FF-1000] and [FF-2000]')).toBe('FF-1000')
  })

  it('does not match lowercase prefixes', () => {
    expect(extractTicketKey('[ff-1000]')).toBeNull()
  })
})

// ---------------------------------------------------------------------------
// getTimeline
// ---------------------------------------------------------------------------

describe('getTimeline', () => {
  it('includes only non-null timestamps', () => {
    const detail = makeDetail({
      created_at: '2026-01-01T00:00:00Z',
      published_at: '2026-01-02T00:00:00Z',
      claimed_at: null,
      started_at: '2026-01-03T00:00:00Z',
      completed_at: null,
      failed_at: null,
      blocked_at: null,
      cancelled_at: null,
      expires_at: null,
    })
    const timeline = getTimeline(detail)
    const labels = timeline.map((e) => e.label)
    expect(labels).toEqual(['Created', 'Published', 'Started'])
  })

  it('sorts events chronologically by timestamp', () => {
    const detail = makeDetail({
      created_at: '2026-03-01T00:00:00Z',
      published_at: '2026-01-01T00:00:00Z',
      started_at: '2026-02-01T00:00:00Z',
    })
    const timeline = getTimeline(detail)
    expect(timeline.map((e) => e.label)).toEqual([
      'Published',
      'Started',
      'Created',
    ])
  })

  it('returns empty array when all timestamps are null', () => {
    const detail = makeDetail({
      created_at: '2026-01-01T00:00:00Z',
      published_at: null,
      claimed_at: null,
      started_at: null,
      completed_at: null,
      failed_at: null,
      blocked_at: null,
      cancelled_at: null,
      expires_at: null,
    })
    // created_at is always non-null in Job, so it will be included
    const timeline = getTimeline(detail)
    expect(timeline).toHaveLength(1)
    expect(timeline[0].label).toBe('Created')
  })

  it('includes all events when all timestamps are set', () => {
    const detail = makeDetail({
      created_at: '2026-01-01T00:00:00Z',
      published_at: '2026-01-02T00:00:00Z',
      claimed_at: '2026-01-03T00:00:00Z',
      started_at: '2026-01-04T00:00:00Z',
      completed_at: '2026-01-05T00:00:00Z',
      failed_at: '2026-01-06T00:00:00Z',
      blocked_at: '2026-01-07T00:00:00Z',
      cancelled_at: '2026-01-08T00:00:00Z',
      expires_at: '2026-01-09T00:00:00Z',
    })
    const timeline = getTimeline(detail)
    expect(timeline).toHaveLength(9)
  })
})
