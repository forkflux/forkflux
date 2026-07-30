## [1.1.0] - 2026-07-29

### ⚙️ Miscellaneous Tasks

- *(api,ui,mcp)* Remove `claimed` status

### 🐛 Bug Fixes

- *(ui)* Adjust events layout on the job details page
- *(ui)* Refresh onboarding guard state via Outlet context after setup completes
- *(ui)* Reset role form before refresh to preserve error state
- *(ui)* Refresh agents after creation so Continue button enables on step 2

### 🚀 Features

- *(ui)* Add job dependencies section
- *(api, ui)* Add jobs routing section
- *(ui)* Add event details in timeline
- *(ui)* Add json grid view and adjust colors
- *(ui)* Align all job detail fields with backend
- *(ui)* Add dashboard onboarding

### 🚜 Refactor

- *(api)* Mark cli deprecated

## [1.0.0] - 2026-07-28

### 🎨 Styling

- *(ui)* Fix linter issues

### ⚙️ Miscellaneous Tasks

- *(api)* Change mcp api endpoints prefix
- *(api)* Improve exception message

### 🏗️ Build System

- *(api)* Update dependencies
- *(api)* Add ui to main package

### 🐛 Bug Fixes

- *(api)* Deduplicate target_role_ids in register_agent to prevent false not-found errors and unique-constraint violations
- *(api)* Enforce BLOCKED→UNBLOCKED→IN_PROGRESS lifecycle and validate unblock_reason at schema boundary
- *(api)* Improve dag logic
- *(api)* Seed profile record with is_onboarded=true in create_profile_table migration
- *(ui)* Cleanup coverage files and fix review comments
- *(ui)* Lost focus on a new role creation

### 📚 Documentation

- Refactoring

### 🚀 Features

- *(api)* Add dashboard core endpoints
- *(api)* Add update job mcp endpoint
- *(api)* Add option to unblock job
- *(ui)* Create dashboard core
- *(ui)* Consume GET /api/v1/ui/agents/roles endpoint with structured Role type
- *(ui)* Add unblocked job status with unblock form, API integration, and tests
- *(ui)* Add roles and agents pages
- *(ui)* Add favicons + update logo hover styles
- *(ui)* Remove ticket key from the job details page
- *(ui)* Mocks/api switch

### 🚜 Refactor

- *(api)* Dag based workflow

## [0.6.0] - 2026-07-17

### ⚙️ Miscellaneous Tasks

- Add my roles endpoint
- Add `parent_job_id` field to jobs list

### 🐛 Bug Fixes

- Include parent exception message in HandoffJobClaimValidationError
- Allow change status from `failed` to `in_progress`

### 🚀 Features

- Added status `blocked`

## [0.5.0] - 2026-07-15

### 🐛 Bug Fixes

- Make scope-based database path resolution unconditional

### 🚀 Features

- Add `scope` option to quickstart command

## [0.4.0] - 2026-07-11

### ⚙️ Miscellaneous Tasks

- Api jobs list accepts multiple statuses

### 🐛 Bug Fixes

- Tighten stats sampling and remove stats/cli magic cleanups
- Enforce assignment-based routing in board flow
- `change_job_status` endpoint response

### 🚀 Features

- Add cli basic stats
- Add multiple roles support for agents
- Add `claim_next_job` endpoint

## [0.3.0] - 2026-07-07

### ⚙️ Miscellaneous Tasks

- Add role delete confirmation
- Handle foreign-key conflicts on role delete

### 🚀 Features

- Add cli command delete role
- Add cli jobs commands

## [0.2.2] - 2026-07-05

### 🏗️ Build System

- Update api dependencies

## [0.2.1] - 2026-06-23

### 🐛 Bug Fixes

- Env name in quickstart command

## [0.2.0] - 2026-06-21

### 🐛 Bug Fixes

- Handle skill download failures in quickstart

### 🚀 Features

- Add quickstart cli command

## [0.1.0] - 2026-06-20

### ⚙️ Miscellaneous Tasks

- Filter jobs by my role only
- Add phony to Makefile
- Handle empty role key
- Add api services logs
- New job auto claim
- Improve dbs compatibility

### 🎨 Styling

- Linters
- Change attr type

### 🏗️ Build System

- Update project structure & configs for releases

### 🐛 Bug Fixes

- List jobs limit
- Typo
- Api prefix
- Add project urls section to `pyproject.toml`

### 📚 Documentation

- Add `api` & `mcp` readme
- Update readme for `api`

### 🚀 Features

- Add api core
- Add agent endpoints
- Add agent cli commands
- Job creation
- Jobs list endpoint
- Add job details endpoint
- Job claim endpoint
- Job change status
- Mcp jobs list
- Mcp tool to change job status
- Mcp squash workflow
- Update slash command and mcp tool description
- Add quickstart commands
- Add sqlite support

### 🧪 Testing

- Add test for change job status to failed
