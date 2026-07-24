/**
 * Shared test utilities for the dashboard test suite.
 *
 * - `renderWithRouter`: wraps a component in a `MemoryRouter` so hooks like
 *   `useSearchParams` and `useNavigate` work in tests.
 * - `createMockJob` / `createMockJobDetail`: fixture builders with sensible
 *   defaults, so individual tests only override the fields they care about.
 * - `createMockJobService`: returns a fully-mocked `JobDataSource` whose
 *   methods are `vi.fn()` stubs with default resolved values.
 */

import { render, type RenderOptions } from '@testing-library/react'
import type { ReactElement, ReactNode } from 'react'
import { MemoryRouter, Route, Routes, type MemoryRouterProps } from 'react-router-dom'
import { vi } from 'vitest'
import type { JobDataSource } from '../services/types.ts'
import type {
  Job,
  JobDetail,
  JobListMeta,
  JobListQuery,
  JobListResponse,
  Role,
  StatusCount,
} from '../types/job.ts'

// ---------------------------------------------------------------------------
// Router wrapper
// ---------------------------------------------------------------------------

interface RouterRenderOptions extends RenderOptions {
  routerProps?: Omit<MemoryRouterProps, 'children'>
}

/**
 * Render a React element wrapped in a `MemoryRouter`.
 *
 * Pass `routerProps.initialEntries` to control the starting URL (useful for
 * testing URL-param parsing and route matching).
 */
export function renderWithRouter(
  ui: ReactElement,
  { routerProps, ...renderOptions }: RouterRenderOptions = {},
) {
  function Wrapper({ children }: { children: ReactNode }) {
    return <MemoryRouter {...routerProps}>{children}</MemoryRouter>
  }
  return render(ui, { wrapper: Wrapper, ...renderOptions })
}

/**
 * Render a React element wrapped in a `MemoryRouter` + `Routes` + `Route`.
 *
 * This is needed for components that use `useParams()` (e.g. `JobDetailPage`),
 * because `useParams` only returns values when the component is rendered inside
 * a matching `<Route>`.
 *
 * @param ui           The element to render at the route.
 * @param path         The route path pattern (e.g. "/jobs/:id").
 * @param initialEntry The initial URL (e.g. "/jobs/42").
 */
export function renderWithRoutes(
  ui: ReactElement,
  path: string,
  initialEntry: string,
  renderOptions?: RenderOptions,
) {
  function Wrapper() {
    return (
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path={path} element={ui} />
        </Routes>
      </MemoryRouter>
    )
  }
  // Pass a fragment as the render target — the actual UI is rendered
  // inside the Route via the Wrapper, so we avoid double-rendering.
  return render(<></>, { wrapper: Wrapper, ...renderOptions })
}

// ---------------------------------------------------------------------------
// Fixture builders
// ---------------------------------------------------------------------------

/**
 * Build a `Job` fixture. All fields have sensible defaults; pass an overrides
 * object to customize only the fields relevant to the test.
 */
export function createMockJob(overrides: Partial<Job> = {}): Job {
  return {
    id: 1,
    parent_job_id: null,
    parent_job_summary: null,
    summary: 'Test job summary [FF-1000]',
    status: 'published',
    priority: 20,
    source_agent_label: 'source-agent',
    assignee_agent_label: null,
    target_role_label: 'Frontend Engineer',
    created_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

/**
 * Build a `Role` fixture. All fields have sensible defaults; pass an overrides
 * object to customize only the fields relevant to the test.
 */
export function createMockRole(overrides: Partial<Role> = {}): Role {
  return {
    id: 1,
    role_key: 'frontend',
    role_label: 'Frontend Engineer',
    created_at: '2026-07-16T10:00:00Z',
    ...overrides,
  }
}

/**
 * Build a `JobDetail` fixture. Extends `Job` with context, constraints,
 * artifacts, and lifecycle timestamps.
 */
export function createMockJobDetail(overrides: Partial<JobDetail> = {}): JobDetail {
  return {
    ...createMockJob(overrides),
    context_payload: { key: 'value' },
    constraints: ['Constraint one', 'Constraint two'],
    artifacts: [],
    failure_reason: null,
    blocked_reason: null,
    published_at: '2026-01-01T00:01:00Z',
    claimed_at: null,
    started_at: null,
    completed_at: null,
    failed_at: null,
    blocked_at: null,
    cancelled_at: null,
    expires_at: null,
    updated_at: '2026-01-01T00:02:00Z',
    ...overrides,
  }
}

// ---------------------------------------------------------------------------
// Mocked jobService
// ---------------------------------------------------------------------------

const DEFAULT_QUERY: JobListQuery = {
  status: 'all',
  role: 'all',
  search: '',
  sort: 'created_at',
  dir: 'desc',
  limit: 50,
  offset: 0,
}

const DEFAULT_LIST_RESPONSE: JobListResponse = {
  items: [],
  total: 0,
  limit: 50,
  offset: 0,
}

const DEFAULT_META: JobListMeta = {
  statuses: [],
  roles: [],
}

const DEFAULT_COUNTS: StatusCount[] = [
  { status: 'all', count: 0 },
  { status: 'published', count: 0 },
  { status: 'claimed', count: 0 },
  { status: 'in_progress', count: 0 },
  { status: 'blocked', count: 0 },
  { status: 'completed', count: 0 },
  { status: 'failed', count: 0 },
  { status: 'cancelled', count: 0 },
]

/**
 * Create a fully-mocked `JobDataSource`. Each method is a `vi.fn()` with a
 * default resolved value; tests can override individual methods as needed.
 */
export function createMockJobService(
  overrides: Partial<JobDataSource> = {},
): JobDataSource {
  return {
    fetchJobs: vi.fn().mockResolvedValue(DEFAULT_LIST_RESPONSE),
    fetchListMeta: vi.fn().mockResolvedValue(DEFAULT_META),
    fetchJobCounts: vi.fn().mockResolvedValue(DEFAULT_COUNTS),
    fetchJobDetail: vi.fn().mockResolvedValue(null),
    ...overrides,
  }
}

export { DEFAULT_QUERY, DEFAULT_LIST_RESPONSE, DEFAULT_META, DEFAULT_COUNTS }
