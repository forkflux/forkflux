# ForkFlux Dashboard

The web UI for ForkFlux — a React + TypeScript single-page app that lets
operators browse, filter, and inspect handoff jobs across all agent roles.

Built with Vite, React Router, and Vitest. In local development it runs entirely
against bundled mock data, so you can work on the UI with no backend running.

## Prerequisites

- Node.js 18+ (matches the Vite 8 / React 19 toolchain)
- npm 9+

## Setup

```bash
npm install
```

All commands below run from `packages/dashboard`.

## Available Scripts

| Script | Command | What it does |
|--------|---------|--------------|
| `dev` | `npm run dev` | Starts the Vite dev server with HMR. Uses the **mock** data source by default (no backend required). |
| `build` | `npm run build` | Type-checks (`tsc -b`) then produces a production bundle in `dist/`. |
| `preview` | `npm run preview` | Serves the production build locally to verify it before deploy. |
| `lint` | `npm run lint` | Runs ESLint over the whole package. |
| `test` | `npm test` | Runs the Vitest suite once (CI mode). |
| `test:watch` | `npm run test:watch` | Runs Vitest in watch mode during development. |
| `test:coverage` | `npm run test:coverage` | Runs the suite and reports V8 coverage. |

## Testing Workflow

Tests use Vitest with a jsdom environment and `@testing-library/react`. Globals
are enabled, so `describe`, `it`, `expect`, and `vi` are available without
imports. Global setup lives in [`src/test/setup.ts`](src/test/setup.ts), which
registers jest-dom matchers, polyfills `window.matchMedia`, and cleans up the
DOM between tests.

Co-located test files follow the `*.test.ts(x)` convention and are picked up
from anywhere under `src/`. Coverage thresholds are enforced:

- Lines / Statements: 80%
- Functions: 80%
- Branches: 75%

Shared fixtures and helpers live in [`src/test/utils.tsx`](src/test/utils.tsx):

- `renderWithRouter` — wraps a component in a `MemoryRouter` so router hooks
  (`useSearchParams`, `useNavigate`) work in tests.
- `renderWithRoute` — renders inside a matching `<Route>`, required for
  components that call `useParams()` (e.g. `JobDetailPage`).
- `createMockJob` / `createMockJobDetail` — fixture builders with sensible
  defaults; override only the fields a test cares about.
- `createMockJobService` — a fully-stubbed `JobDataSource` whose methods are
  `vi.fn()`s returning default resolved values.

## Routes

Routing is defined in [`src/App.tsx`](src/App.tsx) using React Router:

| Path | Component | Notes |
|------|-----------|-------|
| `/` | — | Redirects to `/jobs`. |
| `/jobs` | `JobListPage` | Paginated, filterable job list. |
| `/jobs/:id` | `JobDetailPage` | Full detail view for a single job. |
| `*` | `NotFoundPage` | Catch-all 404. |

The job list is URL-driven: filters, sort, and pagination live in the query
string (see [`useJobListParams`](src/hooks/useJobListParams/useJobListParams.ts)),
so views are shareable and bookmarkable. Supported params are `status`, `role`,
`search`, `sort`, `dir`, `limit`, and `offset`. Changing any filter or the page
size resets `offset` to `0`.

## Mock vs API Behavior

The dashboard talks to a single [`jobService`](src/services/jobService.ts)
instance. Which data source it uses is decided at startup:

- **Dev mode with no `VITE_API_BASE_URL`** → the **mock** data source. This is
  the default for `npm run dev` and needs no backend.
- **Any other case** (production build, preview, or dev with an explicit API
  URL) → the **API** data source, which requires `VITE_API_BASE_URL`.

### Mock data source

Reads from the JSON fixtures in [`mocks/`](mocks/):

- `mocks/jobs.json` — the full list dataset, imported statically.
- `mocks/details/[id].json` — per-job detail, loaded on demand via Vite's
  dynamic `import()` so only the requested detail is fetched.

The mock simulates server-side filtering, sorting, and pagination over the full
local dataset, so dev mode behaves like the real API: the caller receives a
single page plus a `total` count.

### API data source

Calls the live ForkFlux API. The base URL comes from `VITE_API_BASE_URL`
(trailing slash trimmed). If it is unset in a non-dev environment, requests
throw. Endpoints used:

- `GET {base}/ui/jobs` — paginated job list. Query params: `limit`, `offset`,
  `order` (e.g. `created_at_desc`), `my_roles_only=false`, plus optional
  `status` and `target_role_key` filters. Returns `{ items, total, limit, offset }`.
- `GET {base}/ui/jobs/counts` — global per-status counts (always returns every
  status, initialized to 0 when empty).
- `GET {base}/ui/jobs/{id}` — full job detail. A 404 resolves to `null`.

> **Note:** Text search is currently client-side only — the backend does not yet
> expose a search parameter, so the search box filters the current page. When the
> backend adds support, the `search` param will be forwarded in
  [`apiDataSource.ts`](src/services/apiDataSource.ts).

To point dev mode at a real API, set the variable before starting the server:

```bash
VITE_API_BASE_URL=https://api.example.com/api/v1 npm run dev
```
