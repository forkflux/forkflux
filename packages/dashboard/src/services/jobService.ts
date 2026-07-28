/**
 * Backwards-compatible production entry point.
 *
 * Application code imports `@job-service`; Vite aliases that specifier to
 * `jobService.mock.ts` only for mocked development. Keeping this file as a
 * production-only re-export preserves direct imports for consumers/tests.
 */

export { jobService } from './jobService.api.ts';
export type { JobDataSource } from './types.ts';
