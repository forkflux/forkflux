/**
 * Mocked-development job-service entry point.
 */

import { mockDataSource } from './mockDataSource.ts';
import type { JobDataSource } from './types.ts';

export const jobService: JobDataSource = mockDataSource;

export type { JobDataSource } from './types.ts';
