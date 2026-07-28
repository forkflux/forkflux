/**
 * Production job-service entry point.
 *
 * Keep this module free of mock imports so production builds do not resolve
 * the local fixture tree.
 */

import { apiDataSource } from './apiDataSource.ts';
import type { JobDataSource } from './types.ts';

export const jobService: JobDataSource = apiDataSource;

export type { JobDataSource } from './types.ts';
