/**
 * Job service — environment-aware factory.
 *
 * Exposes a single `jobService` instance that components consume. In local
 * development (`import.meta.env.DEV` with no API base URL configured) it
 * uses the mock data source; in all other environments it uses the live API
 * data source.
 *
 * Components import `jobService` and call its methods — they never need to
 * know which data source is active.
 */

import { apiDataSource } from './apiDataSource.ts';
import { mockDataSource } from './mockDataSource.ts';
import type { JobDataSource } from './types.ts';

/**
 * Resolve the active data source.
 *
 * - `DEV` mode without `VITE_API_BASE_URL` → mock (local development)
 * - Otherwise → API (staging, production, or dev with explicit API URL)
 */
function resolveDataSource(): JobDataSource {
  const isDev = import.meta.env.DEV;
  const hasApiUrl = Boolean(import.meta.env.VITE_API_BASE_URL);

  if (isDev && !hasApiUrl) {
    return mockDataSource;
  }
  return apiDataSource;
}

export const jobService: JobDataSource = resolveDataSource();

// Re-export the interface and types for convenience.
export type { JobDataSource } from './types.ts';
