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
