/**
 * API data source — live ForkFlux API.
 *
 * Calls the live ForkFlux API. The base URL is configured via the
 * `FE_API_BASE_URL` environment variable. All endpoints return JSON that
 * matches the types in `src/types/job.ts`.
 *
 * The jobs list endpoint returns a paginated envelope:
 * `{ items, total, limit, offset }`.
 */

import { toStatusCounts } from '../lib/jobs/jobs.ts';
import type {
  Agent,
  CreateAgentRequest,
  CreateAgentResponse,
  CreateProfileRequest,
  CreateRoleRequest,
  GetProfileResponse,
  JobDetail,
  JobListMeta,
  JobListQuery,
  JobListResponse,
  JobSortField,
  JobStatusCountsResponse,
  Role,
  SortDirection,
  StatusCount,
  UnblockJobRequest,
  UnblockJobResponse,
  UpdateRoleRequest,
} from '../types/job.ts';
import type { JobDataSource } from './types.ts';

const API_BASE_URL = (import.meta.env.FE_API_BASE_URL as string | undefined) || '/api/v1';

function getBaseUrl(): string {
  return API_BASE_URL.replace(/\/$/, '');
}

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Request failed: ${res.status} ${res.statusText} (${url})`);
  }
  return (await res.json()) as T;
}

/**
 * Send a JSON POST request and return the parsed response.
 *
 * Unlike `fetchJson`, this returns the raw `Response` so callers can inspect
 * the status code before deciding how to handle errors (e.g. distinguishing
 * 404 from 422 for the unblock endpoint).
 */
async function postJson(url: string, body: unknown): Promise<Response> {
  return sendJson('POST', url, body);
}

/**
 * Send a JSON request with the given HTTP method and return the raw
 * `Response`. Used by `postJson` (POST) and the role-update flow (PATCH).
 */
async function sendJson(
  method: string,
  url: string,
  body: unknown,
): Promise<Response> {
  return fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

/**
 * Send a JSON PATCH request and return the raw `Response`.
 *
 * Used by `updateRole` to edit a role without pulling the shared
 * `body`-libraries.
 */
async function patchJson(url: string, body: unknown): Promise<Response> {
  return sendJson('PATCH', url, body);
}

/**
 * Map the dashboard's sort field + direction to the backend's `order` enum
 * values (e.g. `created_at_desc`). The backend accepts repeated `order`
 * query params; we send a single primary order.
 */
function toOrderParam(sort: JobSortField, dir: SortDirection): string {
  return `${sort}_${dir}`;
}

/**
 * Fetch the roles list from the `GET /api/v1/ui/agents/roles` endpoint.
 *
 * Centralized so that `fetchListMeta` and `fetchRoles` share the same
 * endpoint URL and response typing — avoiding drift between the two
 * call sites.
 */
function fetchRolesFromApi(): Promise<Role[]> {
  return fetchJson<Role[]>(`${getBaseUrl()}/ui/agents/roles`);
}

/**
 * Shape of a single validation error item in a FastAPI 422 `detail` array.
 *
 * The backend's `BaseValidationError` handler returns
 * `{ detail: [{ loc, msg, type, input, ctx }] }`. The `type` field
 * distinguishes conflict errors (`"target_role.conflict"`) from standard
 * Pydantic validation errors (e.g. `"string_too_long"`).
 */
interface ValidationErrorItem {
  type: string;
  msg: string;
  loc: (string | number)[];
}

interface ValidationErrorResponse {
  detail: ValidationErrorItem[];
}

/** Backend error code for a duplicate role-key conflict. */
const ROLE_CONFLICT_CODE = 'target_role.conflict';

/** Backend error code for a target-role-not-found on agent creation. */
const ROLE_NOT_FOUND_CODE = 'target_role.not_found';

/** Backend error code for a target-role-not-found on role update. */
const ROLE_UPDATE_NOT_FOUND_CODE = 'target_role.not_found';

/** Maximum length enforced by the backend `CreateRoleRequest` schema. */
const ROLE_FIELD_MAX_LENGTH = 255;

/** Maximum length enforced by the backend `CreateAgentRequest` schema. */
const AGENT_FIELD_MAX_LENGTH = 255;

/**
 * Build the query string for the jobs list endpoint from a `JobListQuery`.
 *
 * - `status` is omitted when `all` (no status filter).
 * - `target_role_key` is omitted when `all`.
 * - `search` is omitted when empty — the backend does not yet support a
 *   search param, so client-side search applies to the current page only.
 *   When the backend adds it, send `query.search` here (one-line change).
 * - `my_roles_only=false` — the dashboard is an admin view across all roles.
 */
function buildJobsQueryString(query: JobListQuery): string {
  const params = new URLSearchParams();

  params.set('limit', String(query.limit));
  params.set('offset', String(query.offset));
  params.set('order', toOrderParam(query.sort, query.dir));
  params.set('my_roles_only', 'false');

  if (query.status !== 'all') {
    params.set('status', query.status);
  }
  if (query.role !== 'all') {
    params.set('target_role_key', query.role);
  }

  return params.toString();
}

export const apiDataSource: JobDataSource = {
  fetchJobs(query: JobListQuery): Promise<JobListResponse> {
    const qs = buildJobsQueryString(query);
    return fetchJson<JobListResponse>(`${getBaseUrl()}/ui/jobs?${qs}`);
  },

  /**
   * Fetch the list of target roles from the
   * `GET /api/v1/ui/agents/roles` endpoint.
   *
   * This endpoint requires **no authentication** — no Authorization header is
   * sent. The response is a JSON array of `{ id, role_key, role_label,
   * created_at }` objects. An empty array (HTTP 200 with `[]`) is a valid
   * response when no roles exist.
   *
   * Status counts are now sourced from `fetchJobCounts()` (the dedicated
   * `GET /ui/jobs/counts` endpoint), so `statuses` is left empty here.
   */
  async fetchListMeta(_query: JobListQuery): Promise<JobListMeta> {
    const roles = await fetchRolesFromApi();
    return { statuses: [], roles };
  },

  /**
   * Fetch global job counts per status from the
   * `GET /api/v1/ui/jobs/counts` endpoint.
   *
   * The backend always returns all 7 `JobStatusEnum` values initialized to
   * 0, so every status is present even when there are no jobs in that
   * state. The response is normalized into a `StatusCount[]` (with an `all`
   * total) via the shared `toStatusCounts` core helper.
   */
  async fetchJobCounts(): Promise<StatusCount[]> {
    const res = await fetchJson<JobStatusCountsResponse>(
      `${getBaseUrl()}/ui/jobs/counts`,
    );
    return toStatusCounts(res.counts as Record<string, number>);
  },

  async fetchJobDetail(id: number): Promise<JobDetail | null> {
    try {
      return await fetchJson<JobDetail>(`${getBaseUrl()}/ui/jobs/${id}`);
    } catch (err) {
      if (err instanceof Error && err.message.includes('404')) return null;
      throw err;
    }
  },

  /**
   * Unblock a blocked job via `POST /api/v1/ui/jobs/{id}/unblock`.
   *
   * Sends the `unblock_reason` as JSON body. On success (200) returns the
   * parsed `UnblockJobResponse`. Throws typed errors for 404 and 422 so the
   * UI can display user-friendly messages:
   * - 404 → "Job not found"
   * - 422 → "This job cannot be unblocked from its current status"
   */
  async unblockJob(
    id: number,
    unblockReason: string,
  ): Promise<UnblockJobResponse> {
    const body: UnblockJobRequest = { unblock_reason: unblockReason };
    const res = await postJson(
      `${getBaseUrl()}/ui/jobs/${id}/unblock`,
      body,
    );

    if (res.status === 404) {
      throw new Error('Job not found');
    }
    if (res.status === 422) {
      throw new Error(
        'This job cannot be unblocked from its current status.',
      );
    }
    if (!res.ok) {
      throw new Error(
        `Request failed: ${res.status} ${res.statusText}`,
      );
    }

    return (await res.json()) as UnblockJobResponse;
  },

  /**
   * Fetch all available target roles from the
   * `GET /api/v1/ui/agents/roles` endpoint.
   *
   * This endpoint requires **no authentication** — no Authorization header is
   * sent. The response is a JSON array of `{ id, role_key, role_label,
   * created_at }` objects. An empty array (HTTP 200 with `[]`) is a valid
   * response when no roles exist.
   */
  fetchRoles(): Promise<Role[]> {
    return fetchRolesFromApi();
  },

  /**
   * Fetch all registered agents from the
   * `GET /api/v1/ui/agents` endpoint.
   *
   * This endpoint requires **no authentication** — no Authorization header is
   * sent. The response is a JSON array of `{ id, agent_label, tool_family,
   * created_at, roles }` objects where `roles` is a list of
   * `{ role_key, role_label }`. An empty array (HTTP 200 with `[]`) is a
   * valid response when no agents exist.
   */
  fetchAgents(): Promise<Agent[]> {
    return fetchJson<Agent[]>(`${getBaseUrl()}/ui/agents`);
  },

  /**
   * Create a new target role via `POST /api/v1/ui/agents/roles`.
   *
   * Sends `role_key` and `role_label` as JSON body. On success (201)
   * returns the created `Role`.
   *
   * Error handling distinguishes two kinds of 422 responses:
   * - **Conflict** (`detail[0].type === "target_role.conflict"`): a role
   *   with the same `role_key` already exists — throws a user-friendly
   *   "already exists" message.
   * - **Validation** (any other 422, e.g. `"string_too_long"`): the input
   *   failed Pydantic validation — throws the backend's error message.
   *
   * Client-side length validation (255 chars) is also performed before
   * the request to give immediate feedback without a round-trip.
   */
  async createRole(roleKey: string, roleLabel: string): Promise<Role> {
    // Client-side validation mirroring the backend's 255-char limit.
    if (roleKey.length > ROLE_FIELD_MAX_LENGTH) {
      throw new Error(
        `Role key must be at most ${ROLE_FIELD_MAX_LENGTH} characters.`,
      );
    }
    if (roleLabel.length > ROLE_FIELD_MAX_LENGTH) {
      throw new Error(
        `Role label must be at most ${ROLE_FIELD_MAX_LENGTH} characters.`,
      );
    }

    const body: CreateRoleRequest = {
      role_key: roleKey,
      role_label: roleLabel,
    };
    const res = await postJson(
      `${getBaseUrl()}/ui/agents/roles`,
      body,
    );

    if (res.status === 422) {
      let errorBody: ValidationErrorResponse | null = null;
      try {
        errorBody = (await res.json()) as ValidationErrorResponse;
      } catch {
        // Response body is not JSON — fall through to generic error.
      }

      const firstError = errorBody?.detail?.[0];
      if (firstError?.type === ROLE_CONFLICT_CODE) {
        throw new Error(
          `A role with the key "${roleKey}" already exists.`,
        );
      }
      // Non-conflict validation error — use the backend's message.
      throw new Error(
        firstError?.msg ?? 'Invalid input. Please check your values.',
      );
    }
    if (!res.ok) {
      throw new Error(
        `Request failed: ${res.status} ${res.statusText}`,
      );
    }

    return (await res.json()) as Role;
  },

  /**
   * Update an existing target role via
   * `PATCH /api/v1/ui/agents/roles/{role_id}`.
   *
   * Sends `role_key` and `role_label` as JSON body. On success (200)
   * returns the updated `Role`.
   *
   * Error handling distinguishes three kinds of 422 responses:
   * - **Not found** (`detail[0].type === "target_role.not_found"`): the
   *   role ID no longer exists — throws a user-friendly "Role not found"
   *   message.
   * - **Conflict** (`detail[0].type === "target_role.conflict"`): another
   *   role already uses the given `role_key` — throws an
   *   "already exists" message.
   * - **Validation** (any other 422, e.g. `"string_too_long"`): the input
   *   failed Pydantic validation — throws the backend's error message.
   *
   * Client-side length validation (255 chars) is also performed before
   * the request to give immediate feedback without a round-trip.
   */
  async updateRole(
    roleId: number,
    roleKey: string,
    roleLabel: string,
  ): Promise<Role> {
    // Client-side validation mirroring the backend's 255-char limit.
    if (roleKey.length > ROLE_FIELD_MAX_LENGTH) {
      throw new Error(
        `Role key must be at most ${ROLE_FIELD_MAX_LENGTH} characters.`,
      );
    }
    if (roleLabel.length > ROLE_FIELD_MAX_LENGTH) {
      throw new Error(
        `Role label must be at most ${ROLE_FIELD_MAX_LENGTH} characters.`,
      );
    }

    const body: UpdateRoleRequest = {
      role_key: roleKey,
      role_label: roleLabel,
    };
    const res = await patchJson(
      `${getBaseUrl()}/ui/agents/roles/${roleId}`,
      body,
    );

    if (res.status === 422) {
      let errorBody: ValidationErrorResponse | null = null;
      try {
        errorBody = (await res.json()) as ValidationErrorResponse;
      } catch {
        // Response body is not JSON — fall through to generic error.
      }

      const firstError = errorBody?.detail?.[0];
      if (firstError?.type === ROLE_UPDATE_NOT_FOUND_CODE) {
        throw new Error(
          'This role no longer exists. Please refresh and try again.',
        );
      }
      if (firstError?.type === ROLE_CONFLICT_CODE) {
        throw new Error(
          `A role with the key "${roleKey}" already exists.`,
        );
      }
      // Non-conflict validation error — use the backend's message.
      throw new Error(
        firstError?.msg ?? 'Invalid input. Please check your values.',
      );
    }
    if (!res.ok) {
      throw new Error(
        `Request failed: ${res.status} ${res.statusText}`,
      );
    }

    return (await res.json()) as Role;
  },

  /**
   * Delete an existing target role via
   * `DELETE /api/v1/ui/agents/roles/{role_id}`.
   *
   * Performs a soft-delete on the backend. On success (204) resolves to
   * `void` — no response body is returned.
   *
   * Error handling distinguishes not-found from other 422 responses:
   * - **Not found** (`detail[0].type === "target_role.not_found"`): the
   *   role ID no longer exists (or was already soft-deleted) — throws a
   *   user-friendly "Role not found" message.
   * - **Other 422**: uses the backend's error message or a fallback.
   */
  async deleteRole(roleId: number): Promise<void> {
    const res = await fetch(`${getBaseUrl()}/ui/agents/roles/${roleId}`, {
      method: 'DELETE',
    });

    // 204 No Content — success, nothing to parse.
    if (res.status === 204) return;

    if (res.status === 422) {
      let errorBody: ValidationErrorResponse | null = null;
      try {
        errorBody = (await res.json()) as ValidationErrorResponse;
      } catch {
        // Response body is not JSON — fall through to generic error.
      }

      const firstError = errorBody?.detail?.[0];
      if (firstError?.type === ROLE_UPDATE_NOT_FOUND_CODE) {
        throw new Error(
          'This role no longer exists. Please refresh and try again.',
        );
      }
      // Non-not-found validation error — use the backend's message.
      throw new Error(
        firstError?.msg ?? 'Invalid input. Please check your values.',
      );
    }
    if (!res.ok) {
      throw new Error(
        `Request failed: ${res.status} ${res.statusText}`,
      );
    }
  },

  /**
   * Create a new agent via `POST /api/v1/ui/agents`.
   *
   * Sends `agent_label`, `tool_family`, and `target_role_ids` as JSON body.
   * On success (201) returns a `CreateAgentResponse` that includes the
   * one-time `api_token`.
   *
   * Error handling distinguishes two kinds of 422 responses:
   * - **Role not found** (`detail[0].type === "target_role.not_found"`): one
   *   or more of the selected role IDs no longer exist — throws a
   *   user-friendly message.
   * - **Validation** (any other 422, e.g. `"string_too_long"`, `"too_short"`):
   *   the input failed Pydantic validation — throws the backend's error
   *   message.
   *
   * Client-side length validation (255 chars) is also performed before
   * the request to give immediate feedback without a round-trip.
   */
  async createAgent(
    agentLabel: string,
    toolFamily: string | null,
    targetRoleIds: number[],
  ): Promise<CreateAgentResponse> {
    // Client-side validation mirroring the backend's 255-char limit.
    if (agentLabel.length > AGENT_FIELD_MAX_LENGTH) {
      throw new Error(
        `Agent label must be at most ${AGENT_FIELD_MAX_LENGTH} characters.`,
      );
    }
    if (toolFamily !== null && toolFamily.length > AGENT_FIELD_MAX_LENGTH) {
      throw new Error(
        `Tool family must be at most ${AGENT_FIELD_MAX_LENGTH} characters.`,
      );
    }

    const body: CreateAgentRequest = {
      agent_label: agentLabel,
      tool_family: toolFamily,
      target_role_ids: targetRoleIds,
    };
    const res = await postJson(`${getBaseUrl()}/ui/agents`, body);

    if (res.status === 422) {
      let errorBody: ValidationErrorResponse | null = null;
      try {
        errorBody = (await res.json()) as ValidationErrorResponse;
      } catch {
        // Response body is not JSON — fall through to generic error.
      }

      const firstError = errorBody?.detail?.[0];
      if (firstError?.type === ROLE_NOT_FOUND_CODE) {
        throw new Error(
          'One or more selected roles no longer exist. Please refresh and try again.',
        );
      }
      // Non-role-not-found validation error — use the backend's message.
      throw new Error(
        firstError?.msg ?? 'Invalid input. Please check your values.',
      );
    }
    if (!res.ok) {
      throw new Error(
        `Request failed: ${res.status} ${res.statusText}`,
      );
    }

    return (await res.json()) as CreateAgentResponse;
  },

  /**
   * Check whether the user has completed onboarding via
   * `GET /api/v1/ui/profile`.
   *
   * Returns `true` if a profile row exists with `is_onboarded=true`,
   * `false` otherwise (including when no profile row exists yet).
   */
  async getProfile(): Promise<boolean> {
    const res = await fetchJson<GetProfileResponse>(
      `${getBaseUrl()}/ui/profile`,
    );
    return res.is_onboarded;
  },

  /**
   * Mark onboarding as complete (or reset it) via
   * `POST /api/v1/ui/profile`.
   *
   * Sends `is_onboarded` as JSON body. On success (201) returns the
   * confirmed value. Throws on 409 (profile already exists).
   */
  async createProfile(isOnboarded: boolean): Promise<boolean> {
    const body: CreateProfileRequest = { is_onboarded: isOnboarded };
    const res = await postJson(`${getBaseUrl()}/ui/profile`, body);

    if (!res.ok) {
      throw new Error(
        `Request failed: ${res.status} ${res.statusText}`,
      );
    }

    const data = (await res.json()) as { is_onboarded: boolean };
    return data.is_onboarded;
  },
};
