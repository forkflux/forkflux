/**
 * Mock data source — local development only.
 *
 * Reads from the JSON files in `mocks/`. The list and roles are imported
 * statically (bundled at build time); detail files are loaded on demand via
 * Vite's dynamic `import()` so only the requested detail is fetched.
 *
 * The list endpoint simulates server-side filtering, sorting, and pagination
 * over the full local dataset so dev mode behaves like the real API: the
 * caller receives a single page plus a `total` count.
 *
 * An in-memory overlay (`jobOverlay`) tracks mutations from `unblockJob`
 * so that subsequent `fetchJobDetail` / `fetchJobs` / `fetchJobCounts` calls
 * reflect the updated state — mirroring how the real API persists changes.
 */

import {
  countJobsByStatus,
  filterJobs,
  sortJobs,
  toStatusCounts,
} from '../lib/jobs/jobs.ts';
import type {
  Agent,
  AgentRoleSummary,
  CreateAgentResponse,
  Job,
  JobDetail,
  JobListMeta,
  JobListQuery,
  JobListResponse,
  Role,
  StatusCount,
  UnblockJobResponse,
} from '../types/job.ts';
import type { JobDataSource } from './types.ts';

import jobsData from '../../mocks/jobs.json' with { type: 'json' };
import rolesData from '../../mocks/roles.json' with { type: 'json' };
import agentsData from '../../mocks/agents.json' with { type: 'json' };

// The mock JSON is the full dataset; cast once at module load.
const ALL_JOBS = jobsData as Job[];
const ALL_ROLES = rolesData as Role[];
const ALL_AGENTS = agentsData as Agent[];

/** Maximum length enforced by the backend `CreateAgentRequest` schema. */
const MOCK_FIELD_MAX_LENGTH = 255;

/**
 * In-memory overlay for mutated job state.
 *
 * When a job is unblocked (or otherwise mutated), the changes are written
 * here keyed by job ID. `fetchJobDetail`, `fetchJobs`, and `fetchJobCounts`
 * all merge this overlay with the static JSON so the UI reflects mutations
 * without reloading the page.
 */
const jobOverlay = new Map<number, Partial<JobDetail>>();

/**
 * In-memory overlay for created or updated roles.
 *
 * When a role is created via `createRole` or updated via `updateRole`,
 * it is stored here so that subsequent `fetchRoles` calls return the
 * current role — mirroring how the real API persists changes. Keyed by
 * `role_key` for duplicate detection. `updateRole` overrides static-JSON
 * roles by writing here, and `fetchRoles`/`fetchListMeta` merge by `id`
 * so an overlay entry shadows the static entry instead of duplicating it.
 */
const roleOverlay = new Map<string, Role>();

/**
 * In-memory set of soft-deleted role IDs.
 *
 * When a role is deleted via `deleteRole`, its ID is added here so that
 * subsequent `fetchRoles`/`fetchListMeta` calls filter it out — mirroring
 * how the real API soft-deletes rows and excludes them from list responses.
 */
const deletedRoleIds = new Set<number>();

/**
 * In-memory overlay for created agents.
 *
 * When an agent is created via `createAgent`, it is appended here so that
 * subsequent `fetchAgents` calls return the new agent — mirroring how the
 * real API persists changes. Keyed by agent `id`.
 */
const agentOverlay = new Map<number, Agent>();

/**
 * In-memory onboarding flag.
 *
 * Defaults to `false` so the onboarding flow triggers on first visit in dev
 * mode. When `createProfile` is called, the flag is updated so subsequent
 * calls to `getProfile` return the new value — mirroring how the real API
 * persists the profile row.
 */
let isOnboarded = false;

/**
 * Return a copy of a job with any overlay mutations applied.
 * Used by `fetchJobs` and `fetchJobCounts` to reflect in-memory state.
 */
function applyOverlayToJob(job: Job): Job {
  const overlay = jobOverlay.get(job.id);
  if (!overlay) return job;
  return { ...job, ...overlay };
}

/**
 * Return a copy of a job detail with any overlay mutations applied.
 * Used by `fetchJobDetail` to reflect in-memory state.
 */
function applyOverlayToDetail(detail: JobDetail): JobDetail {
  const overlay = jobOverlay.get(detail.id);
  return {
    ...detail,
    upstream_dependencies: detail.upstream_dependencies ?? [],
    downstream_dependencies: detail.downstream_dependencies ?? [],
    ...overlay,
  };
}

/**
 * Reset the in-memory overlay. Test-only utility to ensure test isolation —
 * the module-level `jobOverlay` Map persists across tests otherwise.
 */
export function __resetMockState(): void {
  jobOverlay.clear();
  roleOverlay.clear();
  deletedRoleIds.clear();
  agentOverlay.clear();
}

/**
 * Merge the static role list with the in-memory overlay by `id`.
 *
 * `updateRole` writes overlay entries for static-JSON roles (so the
 * updated key/label sticks). A naive concatenate (`[...ALL_ROLES,
 * ...overlay]`) would return the role twice: once from the static data
 * and once from the overlay. This helper lets the overlay entry
 * **shadow** the static one by `id` instead — matching how the real API
 * returns a single row per role.
 */
function mergeRolesWithOverlay(): Role[] {
  const overlay = Array.from(roleOverlay.values());
  const overlayIds = new Set(overlay.map((r) => r.id));
  const staticNotOverridden = ALL_ROLES.filter(
    (r) => !overlayIds.has(r.id) && !deletedRoleIds.has(r.id),
  );
  const overlayNotDeleted = overlay.filter((r) => !deletedRoleIds.has(r.id));
  return [...staticNotOverridden, ...overlayNotDeleted];
}

export const mockDataSource: JobDataSource = {
  fetchJobs(query: JobListQuery): Promise<JobListResponse> {
    // The role filter value is a `role_key` (e.g. "frontend"), but mock jobs
    // only carry `target_role_label`. Resolve the key to its label so the
    // existing `filterJobs` (which compares labels) works correctly.
    let roleLabel = query.role;
    if (query.role !== 'all') {
      const match = ALL_ROLES.find((r) => r.role_key === query.role);
      roleLabel = match ? match.role_label : query.role;
    }

    // Apply overlay mutations to the static dataset before filtering.
    const jobsWithOverlay = ALL_JOBS.map(applyOverlayToJob);

    // 1. Filter by status, role, and search (server-side semantics).
    const filtered = filterJobs(jobsWithOverlay, {
      status: query.status,
      role: roleLabel,
      search: query.search,
    });

    // 2. Sort by the requested field/direction.
    const sorted = sortJobs(filtered, query.sort, query.dir);

    const total = sorted.length;

    // 3. Clamp offset into [0, total] so an out-of-range offset (e.g. after a
    //    filter narrows results) yields an empty page rather than throwing.
    const safeOffset = Math.min(Math.max(query.offset, 0), total);
    const items = sorted.slice(safeOffset, safeOffset + query.limit);

    return Promise.resolve({
      items,
      total,
      limit: query.limit,
      offset: safeOffset,
    });
  },

  fetchListMeta(_query: JobListQuery): Promise<JobListMeta> {
    // Roles are sourced from the mock roles JSON merged with any roles
    // created or updated via `createRole`/`updateRole` in the current
    // session — matching `fetchRoles` so job-list metadata stays
    // consistent after role mutation. `mergeRolesWithOverlay` shadows
    // static-JSON roles with their updated overlay entries. Status
    // counts are sourced from `fetchJobCounts()` (the dedicated counts
    // endpoint), so `statuses` is left empty here.
    return Promise.resolve({
      statuses: [],
      roles: mergeRolesWithOverlay(),
    });
  },

  /**
   * Global job counts per status over the full mock dataset. Mirrors the
   * backend `count_by_status` contract: all 9 statuses are present,
   * initialized to 0 when there are no jobs in that state.
   *
   * Applies the in-memory overlay so counts reflect mutations (e.g. a job
   * unblocked in the current session moves from `blocked` to `unblocked`).
   */
  fetchJobCounts(): Promise<StatusCount[]> {
    const jobsWithOverlay = ALL_JOBS.map(applyOverlayToJob);
    return Promise.resolve(toStatusCounts(countJobsByStatus(jobsWithOverlay)));
  },

  async fetchJobDetail(id: number): Promise<JobDetail | null> {
    try {
      const mod = await import(
        /* @vite-ignore */ `../../mocks/details/${id}.json`
      );
      const detail = mod.default as JobDetail;
      // Merge any in-memory overlay mutations (e.g. from unblockJob).
      return applyOverlayToDetail(detail);
    } catch {
      return null;
    }
  },

  /**
   * Unblock a blocked job (mock). Mirrors the API data source contract:
   * returns a mock `UnblockJobResponse` with `new_status: 'unblocked'`
   * and `previous_status: 'blocked'`. Throws the same typed errors as the
   * API source for 404/422 parity.
   *
   * Persists the mutation to the in-memory overlay so subsequent
   * `fetchJobDetail` calls return the updated `unblocked` status,
   * `unblock_reason`, and `unblocked_at` — mirroring the real API.
   */
  async unblockJob(
    id: number,
    unblockReason: string,
  ): Promise<UnblockJobResponse> {
    // Simulate a small delay for realism.
    await new Promise((r) => setTimeout(r, 100));

    const staticJob = ALL_JOBS.find((j) => j.id === id);
    if (!staticJob) {
      throw new Error('Job not found');
    }

    // Check the overlay-mutated state, not the static JSON.
    const job = applyOverlayToJob(staticJob);
    if (job.status !== 'blocked') {
      throw new Error(
        'This job cannot be unblocked from its current status.',
      );
    }

    // Persist the mutation to the in-memory overlay.
    const now = new Date().toISOString();
    jobOverlay.set(id, {
      status: 'unblocked',
      unblock_reason: unblockReason,
      unblocked_at: now,
      blocked_reason: null,
      blocked_at: null,
      updated_at: now,
    });

    return {
      job_id: id,
      previous_status: 'blocked',
      new_status: 'unblocked',
      unblock_reason: unblockReason,
    };
  },

  /**
   * Return all roles from the mock roles JSON, merged with any roles
   * created via `createRole` in the current session. Mirrors the
   * `GET /api/v1/ui/agents/roles` endpoint contract.
   */
  fetchRoles(): Promise<Role[]> {
    return Promise.resolve(mergeRolesWithOverlay());
  },

  /**
   * Return all agents from the mock agents JSON. Mirrors the
   * `GET /api/v1/ui/agents` endpoint contract — returns an `Agent[]`
   * with `id`, `agent_label`, `tool_family`, `created_at`, and `roles`.
   */
  fetchAgents(): Promise<Agent[]> {
    const created = Array.from(agentOverlay.values());
    return Promise.resolve([...ALL_AGENTS, ...created]);
  },

  /**
   * Create a new target role (mock). Mirrors the API data source contract:
   * returns a mock `Role` with the provided `role_key` and `role_label`.
   * Throws a typed error when a role with the same `role_key` already
   * exists (in the static JSON or the in-memory overlay).
   *
   * Persists the new role to the in-memory overlay so subsequent
   * `fetchRoles` calls return it — mirroring the real API.
   */
  async createRole(roleKey: string, roleLabel: string): Promise<Role> {
    // Simulate a small delay for realism.
    await new Promise((r) => setTimeout(r, 100));

    const key = roleKey.trim();
    const label = roleLabel.trim();

    // Check for duplicates in both the static JSON and the overlay.
    const exists =
      ALL_ROLES.some((r) => r.role_key === key) ||
      roleOverlay.has(key);
    if (exists) {
      throw new Error(`A role with the key "${key}" already exists.`);
    }

    const role: Role = {
      id: Date.now(),
      role_key: key,
      role_label: label,
      created_at: new Date().toISOString(),
    };

    roleOverlay.set(key, role);
    return role;
  },

  /**
   * Update an existing target role (mock). Mirrors the API data source
   * contract: returns the updated `Role` with the new `role_key` and
   * `role_label`. Throws a typed error when the role ID does not exist,
   * or when the new `role_key` is already taken by another role.
   *
   * Persisted to the in-memory overlay so subsequent `fetchRoles` calls
   * return the updated role — mirroring the real API. When the
   * `role_key` changes, the old overlay entry is removed.
   */
  async updateRole(
    roleId: number,
    roleKey: string,
    roleLabel: string,
  ): Promise<Role> {
    // Simulate a small delay for realism.
    await new Promise((r) => setTimeout(r, 100));

    const key = roleKey.trim();
    const label = roleLabel.trim();

    // Client-side length validation mirroring the backend's 255-char
    // limit and the API data source — keeps mock and API behavior
    // aligned.
    if (key.length > MOCK_FIELD_MAX_LENGTH) {
      throw new Error(
        `Role key must be at most ${MOCK_FIELD_MAX_LENGTH} characters.`,
      );
    }
    if (label.length > MOCK_FIELD_MAX_LENGTH) {
      throw new Error(
        `Role label must be at most ${MOCK_FIELD_MAX_LENGTH} characters.`,
      );
    }

    // Use the merged, deletion-aware active role list for both the
    // existing-role lookup and the duplicate-key conflict check.
    // `mergeRolesWithOverlay` shadows static entries with overlay entries
    // by `id` and excludes `deletedRoleIds`, so:
    //   • soft-deleted roles can't be looked up (hence can't be updated),
    //   • renamed overlay entries expose their current key (no stale-key
    //     false positives), and
    //   • keys from deleted roles are reusable (they're filtered out of
    //     the conflict pool).
    const activeRoles = mergeRolesWithOverlay();
    const existing = activeRoles.find((r) => r.id === roleId);
    if (!existing) {
      throw new Error(
        'This role no longer exists. Please refresh and try again.',
      );
    }

    // If the role_key changed, ensure no active (non-deleted) role already
    // uses it.
    const conflict = activeRoles.some(
      (r) => r.id !== roleId && r.role_key === key,
    );
    if (conflict) {
      throw new Error(`A role with the key "${key}" already exists.`);
    }

    // When the role_key changed, remove the old overlay entry so the
    // stale key doesn't linger in fetchRoles results. Always set the
    // updated (or new) overlay entry under the new key.
    if (existing.role_key !== key && roleOverlay.has(existing.role_key)) {
      roleOverlay.delete(existing.role_key);
    }

    const updated: Role = {
      ...existing,
      role_key: key,
      role_label: label,
    };
    roleOverlay.set(key, updated);
    return updated;
  },

  /**
   * Delete an existing target role (mock). Mirrors the API data source
   * contract: performs a soft-delete by adding the role ID to the
   * in-memory `deletedRoleIds` set so that subsequent `fetchRoles`
   * calls exclude it — mirroring the real API's soft-delete behavior.
   *
   * Throws a typed error when the role ID does not exist or was already
   * deleted, matching the API source and the backend's 422
   * `target_role.not_found` response.
   */
  async deleteRole(roleId: number): Promise<void> {
    // Simulate a small delay for realism.
    await new Promise((r) => setTimeout(r, 100));

    // Check if already deleted — a second delete should fail.
    if (deletedRoleIds.has(roleId)) {
      throw new Error(
        'This role no longer exists. Please refresh and try again.',
      );
    }

    // Find the role by ID in overlay or static JSON.
    const overlayRoles = Array.from(roleOverlay.values());
    const existing =
      overlayRoles.find((r) => r.id === roleId) ??
      ALL_ROLES.find((r) => r.id === roleId);
    if (!existing) {
      throw new Error(
        'This role no longer exists. Please refresh and try again.',
      );
    }

    deletedRoleIds.add(roleId);
  },

  /**
   * Create a new agent (mock). Mirrors the API data source contract:
   * returns a mock `CreateAgentResponse` with a fake one-time `api_token`.
   *
   * Validation mirrors the API data source and the backend Pydantic schema:
   * - `agent_label` must be non-blank and at most 255 characters.
   * - `tool_family` (when provided) must be at most 255 characters.
   * - `target_role_ids` must contain at least one ID.
   * - Each role ID must exist in the static JSON or the in-memory overlay.
   *
   * Persists the new agent to the in-memory overlay so subsequent
   * `fetchAgents` calls return it — mirroring the real API.
   */
  async createAgent(
    agentLabel: string,
    toolFamily: string | null,
    targetRoleIds: number[],
  ): Promise<CreateAgentResponse> {
    // Simulate a small delay for realism.
    await new Promise((r) => setTimeout(r, 100));

    const label = agentLabel.trim();

    // Client-side validation mirroring the backend's 255-char limit and
    // the API data source — keeps mock and API behavior aligned.
    if (label.length > MOCK_FIELD_MAX_LENGTH) {
      throw new Error(
        `Agent label must be at most ${MOCK_FIELD_MAX_LENGTH} characters.`,
      );
    }
    if (toolFamily !== null && toolFamily.length > MOCK_FIELD_MAX_LENGTH) {
      throw new Error(
        `Tool family must be at most ${MOCK_FIELD_MAX_LENGTH} characters.`,
      );
    }
    if (targetRoleIds.length === 0) {
      throw new Error('At least one target role is required.');
    }

    // Resolve role IDs to role summaries, validating that each ID exists.
    const allRoles = [...ALL_ROLES, ...Array.from(roleOverlay.values())];
    const roles: AgentRoleSummary[] = [];
    for (const roleId of targetRoleIds) {
      const role = allRoles.find((r) => r.id === roleId);
      if (!role) {
        throw new Error(
          'One or more selected roles no longer exist. Please refresh and try again.',
        );
      }
      roles.push({
        role_key: role.role_key,
        role_label: role.role_label,
      });
    }

    const id = Date.now();
    const agent: Agent = {
      id,
      agent_label: label,
      tool_family: toolFamily,
      created_at: new Date().toISOString(),
      roles,
    };

    agentOverlay.set(id, agent);

    // Generate a fake one-time token.
    const token = `ff_mock_${Math.random().toString(36).slice(2, 18)}`;

    return {
      agent_id: id,
      agent_label: label,
      tool_family: toolFamily,
      target_role_ids: targetRoleIds,
      api_token: token,
    };
  },

  /**
   * Check whether the user has completed onboarding.
   *
   * Returns the in-memory `isOnboarded` flag. Defaults to `false` so the
   * onboarding flow triggers on first visit.
   */
  getProfile(): Promise<boolean> {
    return Promise.resolve(isOnboarded);
  },

  /**
   * Mark onboarding as complete (or reset it).
   *
   * Updates the in-memory flag and returns the new value — mirroring the
   * real API's `POST /api/v1/ui/profile`.
   */
  createProfile(value: boolean): Promise<boolean> {
    isOnboarded = value;
    return Promise.resolve(isOnboarded);
  },
};
