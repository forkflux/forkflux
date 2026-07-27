/**
 * Job service — environment-aware factory.
 *
 * Exposes a single `jobService` instance that components consume. The active
 * data source is selected via the `FE_USE_MOCKS` environment variable:
 *
 * - `FE_USE_MOCKS === 'true'` → mock data source (in-memory fixtures)
 * - otherwise (unset / any other value) → live API data source (default)
 *
 * The API is the default data source. Mocks are opt-in via
 * `npm run dev:mocked`, which sets `FE_USE_MOCKS=true` inline.
 *
 * Components import `jobService` and call its methods — they never need to
 * know which data source is active.
 */

import { apiDataSource } from './apiDataSource.ts';
import { mockDataSource } from './mockDataSource.ts';
import type { JobDataSource } from './types.ts';

/**
 * Resolve the active data source based on the `FE_USE_MOCKS` flag.
 *
 * - `'true'` → mock (local development with fixture JSON)
 * - otherwise → API (default; staging, production, or dev with API URL)
 */
function resolveDataSource(): JobDataSource {
  const useMocks = import.meta.env.FE_USE_MOCKS === 'true';
  return useMocks ? mockDataSource : apiDataSource;
}

export const jobService: JobDataSource = resolveDataSource();

// Re-export the interface and types for convenience.
export type { JobDataSource } from './types.ts';
