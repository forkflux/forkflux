import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ThemeToggle } from '../../components/ThemeToggle/ThemeToggle'
import { jobService } from '@job-service'
import { formatDate, slugifyRoleKey } from '../../lib/jobs/jobs'
import { useAgents } from '../../store/hooks'
import { useProfile } from '../../store/hooks'
import { useRoles } from '../../store/hooks'
import type { CreateAgentResponse } from '../../types/job'
import './OnboardingPage.scss'

/** MCP server configuration template — token is interpolated at render time. */
function mcpConfigJson(token: string): string {
  return JSON.stringify(
    {
      mcpServers: {
        ff: {
          command: 'uvx',
          args: ['forkflux-mcp'],
          env: {
            FORKFLUX_API_KEY: token,
            FORKFLUX_API_URL: 'http://127.0.0.1:8000/api/v1',
          },
        },
      },
    },
    null,
    2,
  )
}

const TOTAL_STEPS = 3
const DOCS_URL = 'https://docs.forkflux.ai/mcp-integration#client-specific-notes'

export function OnboardingPage() {
  const navigate = useNavigate()
  const { setOnboarded } = useProfile()

  // ── shared state ──────────────────────────────────────────────
  // Roles + agents come from the shared store slices (same slices as
  // RolesPage/AgentsPage), so the onboarding wizard's lists stay in sync with
  // the rest of the app and we avoid a duplicate initial fetch. Per-form
  // `fetch(true)` already bypasses the cache, so no `invalidate` is needed.
  const {
    items: roles,
    isLoading: rolesLoading,
    error: rolesError,
    fetchedAt: rolesFetchedAt,
    fetch: fetchRoles,
  } = useRoles()
  const {
    items: agents,
    isLoading: agentsLoading,
    error: agentsError,
    fetchedAt: agentsFetchedAt,
    fetch: fetchAgents,
  } = useAgents()
  const [step, setStep] = useState(1)
  // `loading`/`error` gate the whole page on the INITIAL fetch only. Both
  // slices load in parallel; the page is loading until both resolve. A slice
  // error is fatal only while that slice has never loaded (`fetchedAt` is
  // `null`) — once it has loaded, a later refresh failure (after a create, a
  // tab return, etc.) is non-fatal so the wizard stays on the current step
  // and the affected form surfaces its own message (see `refreshRoles` and
  // the role form error render; `refreshAgents` and the agent form analog).
  const loading = rolesLoading || agentsLoading
  const error =
    (rolesError && rolesFetchedAt === null
      ? rolesError
      : null) ?? (agentsError && agentsFetchedAt === null ? agentsError : null)

  // ── step 1: role creation ─────────────────────────────────────
  const [roleKey, setRoleKey] = useState('')
  const [roleLabel, setRoleLabel] = useState('')
  const [roleKeyTouched, setRoleKeyTouched] = useState(false)
  const [creatingRole, setCreatingRole] = useState(false)
  const [roleError, setRoleError] = useState<string | null>(null)

  // ── step 2: agent creation ────────────────────────────────────
  const [agentLabel, setAgentLabel] = useState('')
  const [toolFamily, setToolFamily] = useState('')
  const [selectedRoleIds, setSelectedRoleIds] = useState<number[]>([])
  const [creatingAgent, setCreatingAgent] = useState(false)
  const [agentError, setAgentError] = useState<string | null>(null)

  // ── token success view (inside step 2) ────────────────────────
  const [createdAgent, setCreatedAgent] =
    useState<CreateAgentResponse | null>(null)
  const [tokenCopied, setTokenCopied] = useState(false)
  const [mcpCopied, setMcpCopied] = useState(false)
  const [copyFailed, setCopyFailed] = useState(false)
  const tokenInputRef = useRef<HTMLInputElement>(null)

  // ── step 3: finish setup ──────────────────────────────────────
  const [finishing, setFinishing] = useState(false)
  const [finishError, setFinishError] = useState<string | null>(null)

  // ── initial data load ─────────────────────────────────────────
  // Both slices load in parallel via the shared store. `loading`/`error` are
  // derived from the agents slice (agents fetch is the slower of the two).
  useEffect(() => {
    void fetchRoles()
    void fetchAgents()
  }, [fetchRoles, fetchAgents])

  // ── role helpers ──────────────────────────────────────────────
  // Force-refetch the roles slice. The slice never rejects: on failure it
  // records `rolesError` (the supported failure result) instead. The role
  // form renders the form-specific "Failed to refresh roles" message from
  // that slice error (see the role form error block), so this helper no
  // longer needs an (unreachable) `.catch`.
  function refreshRoles() {
    return fetchRoles(true)
  }

  function handleRoleLabelChange(value: string) {
    setRoleLabel(value)
    if (!roleKeyTouched) {
      setRoleKey(slugifyRoleKey(value))
    }
  }

  function handleRoleKeyChange(value: string) {
    setRoleKeyTouched(true)
    setRoleKey(value)
  }

  function resetRoleForm() {
    setRoleKey('')
    setRoleLabel('')
    setRoleKeyTouched(false)
    setRoleError(null)
  }

  async function handleAddRole(e: React.FormEvent) {
    e.preventDefault()

    const trimmedKey = roleKey.trim()
    const trimmedLabel = roleLabel.trim()

    if (!trimmedLabel) {
      setRoleError('Please provide a role label.')
      return
    }
    if (!trimmedKey) {
      setRoleError('Please provide a role key.')
      return
    }

    setCreatingRole(true)
    setRoleError(null)

    try {
      await jobService.createRole(trimmedKey, trimmedLabel)
      resetRoleForm()
      await refreshRoles()
    } catch (err) {
      setRoleError(
        err instanceof Error
          ? err.message
          : 'Failed to create role. Please try again.',
      )
    } finally {
      setCreatingRole(false)
    }
  }

  // ── agent helpers ─────────────────────────────────────────────
  // Force-refetch the agents slice. The slice never rejects: on failure it
  // records `agentsError` (the supported failure result) instead. The agent
  // form renders the form-specific "Failed to refresh agents" message from
  // that slice error (see the agent form error block), so this helper no
  // longer needs an (unreachable) `.catch`.
  function refreshAgents() {
    return fetchAgents(true)
  }

  function toggleRoleId(roleId: number) {
    setSelectedRoleIds((prev) =>
      prev.includes(roleId)
        ? prev.filter((id) => id !== roleId)
        : [...prev, roleId],
    )
  }

  async function handleAddAgent(e: React.FormEvent) {
    e.preventDefault()

    const trimmedLabel = agentLabel.trim()

    if (!trimmedLabel) {
      setAgentError('Please provide an agent label.')
      return
    }
    if (selectedRoleIds.length === 0) {
      setAgentError('Please select at least one role.')
      return
    }

    setCreatingAgent(true)
    setAgentError(null)

    try {
      const result = await jobService.createAgent(
        trimmedLabel,
        toolFamily.trim() || null,
        selectedRoleIds,
      )
      setCreatedAgent(result)
      await refreshAgents()
      setTokenCopied(false)
      setMcpCopied(false)
      setCopyFailed(false)
    } catch (err) {
      setAgentError(
        err instanceof Error
          ? err.message
          : 'Failed to create agent. Please try again.',
      )
    } finally {
      setCreatingAgent(false)
    }
  }

  async function handleCopyToken() {
    if (!createdAgent) return
    try {
      await navigator.clipboard.writeText(createdAgent.api_token)
      setTokenCopied(true)
      setCopyFailed(false)
    } catch {
      setTokenCopied(false)
      setCopyFailed(true)
      tokenInputRef.current?.select()
    }
  }

  async function handleCopyMcpConfig() {
    if (!createdAgent) return
    const config = mcpConfigJson(createdAgent.api_token)
    try {
      await navigator.clipboard.writeText(config)
      setMcpCopied(true)
    } catch {
      // Fallback: user can select manually from the <pre> block.
    }
  }

  /** Reset the agent form so the user can add another agent. */
  function handleAddAnotherAgent() {
    const label = createdAgent
    setCreatedAgent(null)
    // Refresh the list so the new agent appears in the table.
    void refreshAgents()
    // Preserve label for convenience if user wants same tool family.
    setAgentLabel('')
    setToolFamily(label?.tool_family ?? toolFamily)
    setSelectedRoleIds([])
    setAgentError(null)
  }

  // ── finish setup ──────────────────────────────────────────────
  async function handleFinishSetup() {
    setFinishing(true)
    setFinishError(null)
    try {
      await jobService.createProfile(true)
      setOnboarded(true)
      navigate('/jobs', { replace: true })
    } catch (err) {
      setFinishError(
        err instanceof Error
          ? err.message
          : 'Failed to complete setup. Please try again.',
      )
      setFinishing(false)
    }
  }

  // ── navigation ────────────────────────────────────────────────
  function goNext() {
    setStep((s) => Math.min(s + 1, TOTAL_STEPS))
  }

  function goBack() {
    setStep((s) => Math.max(s - 1, 1))
  }

  const canProceedFromStep1 = roles.length >= 1
  const canProceedFromStep2 = agents.length >= 1

  // ── loading / error states ────────────────────────────────────
  if (loading) {
    return (
      <div className="ff-onboarding">
        <div className="ff-onboarding__card">
          <p className="ff-onboarding__loading">Loading…</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="ff-onboarding">
        <div className="ff-onboarding__card ff-onboarding__card--error">
          <p>Error: {error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="ff-onboarding">
      <div className="ff-onboarding__card">
        <div className="ff-onboarding__theme-toggle">
          <ThemeToggle />
        </div>

        <h1 className="ff-onboarding__title">Welcome to ForkFlux</h1>
        <p className="ff-onboarding__subtitle">
          Let's get your workspace set up in a few minutes.
        </p>

        {/* ── step indicators ──────────────────────────────── */}
        <div className="ff-onboarding__steps" aria-label="Progress">
          {Array.from({ length: TOTAL_STEPS }, (_, i) => i + 1).map((n) => (
            <div
              key={n}
              className={`ff-onboarding__step-dot${n === step ? ' ff-onboarding__step-dot--active' : ''}${n < step ? ' ff-onboarding__step-dot--done' : ''}`}
              aria-current={n === step ? 'step' : undefined}
            >
              {n < step ? '✓' : n}
            </div>
          ))}
        </div>

        {/* ── step 1: roles ────────────────────────────────── */}
        {step === 1 && (
          <div className="ff-onboarding__content">
            <h2 className="ff-onboarding__step-title">
              Step 1: Add workflow roles
            </h2>
            <p className="ff-onboarding__step-desc">
              Roles define the types of work your agents can handle. Create at
              least one role to continue.
            </p>

            {/* Existing roles */}
            {roles.length > 0 && (
              <div className="ff-onboarding__table-wrap">
                <table className="ff-onboarding__table">
                  <thead>
                    <tr>
                      <th className="ff-onboarding__th">Key</th>
                      <th className="ff-onboarding__th">Label</th>
                    </tr>
                  </thead>
                  <tbody>
                    {roles.map((r) => (
                      <tr key={r.id} className="ff-onboarding__row">
                        <td className="ff-onboarding__td ff-onboarding__td--mono">
                          {r.role_key}
                        </td>
                        <td className="ff-onboarding__td">{r.role_label}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Add role form */}
            <form
              className="ff-onboarding__form"
              onSubmit={handleAddRole}
              noValidate
            >
              <h3 className="ff-onboarding__form-title">Add a role</h3>

              <label className="ff-onboarding__label" htmlFor="onb-role-label">
                Role Label <span className="ff-onboarding__required">*</span>
              </label>
              <input
                id="onb-role-label"
                type="text"
                className="ff-onboarding__input"
                value={roleLabel}
                onChange={(e) => handleRoleLabelChange(e.target.value)}
                placeholder="e.g. Frontend Engineer"
                disabled={creatingRole}
                required
                aria-describedby={(roleError || (rolesError && rolesFetchedAt)) ? 'onb-role-error' : undefined}
                aria-invalid={(roleError || (rolesError && rolesFetchedAt)) ? true : undefined}
              />

              <label className="ff-onboarding__label" htmlFor="onb-role-key">
                Role Key <span className="ff-onboarding__required">*</span>
              </label>
              <input
                id="onb-role-key"
                type="text"
                className="ff-onboarding__input ff-onboarding__input--mono"
                value={roleKey}
                onChange={(e) => handleRoleKeyChange(e.target.value)}
                placeholder="e.g. frontend_engineer"
                disabled={creatingRole}
                required
                aria-describedby={(roleError || (rolesError && rolesFetchedAt)) ? 'onb-role-error' : undefined}
                aria-invalid={(roleError || (rolesError && rolesFetchedAt)) ? true : undefined}
              />
              {!roleKeyTouched && roleLabel && (
                <p className="ff-onboarding__hint">Auto-generated from label</p>
              )}

              {/* Prefer the form's own validation/create error; fall back to
                  the slice's refresh failure (post-initial-load) surfaced as
                  the form-specific message — mirrors the now-removed
                  unreachable `.catch` in `refreshRoles`. */}
              {(() => {
                const refreshFailed =
                  rolesError !== null && rolesFetchedAt !== null
                const msg = roleError ?? (refreshFailed ? 'Failed to refresh roles' : null)
                if (!msg) return null
                return (
                  <p
                    id="onb-role-error"
                    className="ff-onboarding__form-error"
                    role="alert"
                    aria-live="assertive"
                  >
                    {msg}
                  </p>
                )
              })()}

              <button
                type="submit"
                className="ff-onboarding__add-btn"
                disabled={creatingRole}
              >
                {creatingRole ? 'Adding…' : 'Add Role'}
              </button>
            </form>

            {/* Bottom nav */}
            <div className="ff-onboarding__actions">
              <div />{/* spacer */}
              <button
                type="button"
                className="ff-onboarding__primary-btn"
                disabled={!canProceedFromStep1}
                onClick={goNext}
              >
                Continue
              </button>
            </div>
          </div>
        )}

        {/* ── step 2: agents ───────────────────────────────── */}
        {step === 2 && (
          <div className="ff-onboarding__content">
            <h2 className="ff-onboarding__step-title">
              Step 2: Add agents
            </h2>
            <p className="ff-onboarding__step-desc">
              Agents are AI workers that claim and execute jobs. Each agent
              receives an API token — copy it immediately after creation.
            </p>

            {/* Existing agents */}
            {agents.length > 0 && (
              <div className="ff-onboarding__table-wrap">
                <table className="ff-onboarding__table">
                  <thead>
                    <tr>
                      <th className="ff-onboarding__th">Label</th>
                      <th className="ff-onboarding__th">Roles</th>
                      <th className="ff-onboarding__th">Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {agents.map((a) => (
                      <tr key={a.id} className="ff-onboarding__row">
                        <td className="ff-onboarding__td ff-onboarding__td--mono">
                          {a.agent_label}
                        </td>
                        <td className="ff-onboarding__td">
                          {a.roles.length === 0 ? (
                            '—'
                          ) : (
                            <div className="ff-onboarding__badges">
                              {a.roles.map((r) => (
                                <span
                                  key={r.role_key}
                                  className="ff-onboarding__badge"
                                >
                                  {r.role_label}
                                </span>
                              ))}
                            </div>
                          )}
                        </td>
                        <td className="ff-onboarding__td ff-onboarding__td--muted">
                          {formatDate(a.created_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Agent create form or token success view */}
            {createdAgent ? (
              <div className="ff-onboarding__token-view">
                <h3 className="ff-onboarding__form-title">
                  Agent Created: {createdAgent.agent_label}
                </h3>

                <div
                  className="ff-onboarding__token-warning"
                  role="alert"
                >
                  <strong>⚠ Copy your API token now.</strong> It will not be
                  shown again.
                </div>

                {/* Token copy */}
                <label className="ff-onboarding__label" htmlFor="onb-token">
                  API Token
                </label>
                <div className="ff-onboarding__token-box">
                  <input
                    ref={tokenInputRef}
                    id="onb-token"
                    type="text"
                    className="ff-onboarding__token-input"
                    value={createdAgent.api_token}
                    readOnly
                    onFocus={(e) => e.target.select()}
                  />
                  <button
                    type="button"
                    className="ff-onboarding__copy-btn"
                    onClick={handleCopyToken}
                  >
                    {tokenCopied ? '✓ Copied' : 'Copy'}
                  </button>
                </div>

                {copyFailed && (
                  <p
                    className="ff-onboarding__token-fallback"
                    role="alert"
                    aria-live="assertive"
                  >
                    Automatic copy failed. The token is selected — press
                    Cmd/Ctrl+C to copy it manually.
                  </p>
                )}

                {/* MCP config */}
                <label className="ff-onboarding__label">
                  MCP Server Configuration
                </label>
                <p className="ff-onboarding__step-desc">
                  Use this configuration in your AI client's MCP server JSON:
                </p>
                <div className="ff-onboarding__mcp-box">
                  <pre className="ff-onboarding__mcp-pre">
                    <code>{mcpConfigJson(createdAgent.api_token)}</code>
                  </pre>
                  <button
                    type="button"
                    className="ff-onboarding__copy-btn ff-onboarding__copy-btn--block"
                    onClick={handleCopyMcpConfig}
                  >
                    {mcpCopied ? '✓ Copied' : 'Copy Config'}
                  </button>
                </div>

                <p className="ff-onboarding__docs-link">
                  Or find one-line commands for your AI client at{' '}
                  <a
                    href={DOCS_URL}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    docs.forkflux.ai/mcp-integration
                  </a>
                </p>

                <button
                  type="button"
                  className="ff-onboarding__add-btn"
                  onClick={handleAddAnotherAgent}
                >
                  + Add Another Agent
                </button>
              </div>
            ) : (
              <form
                className="ff-onboarding__form"
                onSubmit={handleAddAgent}
                noValidate
              >
                <h3 className="ff-onboarding__form-title">Add an agent</h3>

                <label className="ff-onboarding__label" htmlFor="onb-agent-label">
                  Agent Label <span className="ff-onboarding__required">*</span>
                </label>
                <input
                  id="onb-agent-label"
                  type="text"
                  className="ff-onboarding__input"
                  value={agentLabel}
                  onChange={(e) => setAgentLabel(e.target.value)}
                  placeholder="e.g. frontend-bot"
                  disabled={creatingAgent}
                  required
                  aria-describedby={(agentError || (agentsError && agentsFetchedAt)) ? 'onb-agent-error' : undefined}
                  aria-invalid={(agentError || (agentsError && agentsFetchedAt)) ? true : undefined}
                />

                <label className="ff-onboarding__label" htmlFor="onb-tool-family">
                  Tool Family
                </label>
                <input
                  id="onb-tool-family"
                  type="text"
                  className="ff-onboarding__input"
                  value={toolFamily}
                  onChange={(e) => setToolFamily(e.target.value)}
                  placeholder="e.g. playwright (optional)"
                  disabled={creatingAgent}
                />

                <fieldset className="ff-onboarding__fieldset">
                  <legend className="ff-onboarding__label">
                    Target Roles <span className="ff-onboarding__required">*</span>
                  </legend>
                  {roles.length === 0 ? (
                    <p className="ff-onboarding__hint">
                      No roles available. Go back to Step 1 to create a role
                      first.
                    </p>
                  ) : (
                    <div className="ff-onboarding__role-list">
                      {roles.map((r) => (
                        <label key={r.id} className="ff-onboarding__role-option">
                          <input
                            type="checkbox"
                            className="ff-onboarding__checkbox"
                            checked={selectedRoleIds.includes(r.id)}
                            onChange={() => toggleRoleId(r.id)}
                            disabled={creatingAgent}
                          />
                          <span className="ff-onboarding__role-label-text">
                            {r.role_label}
                          </span>
                          <span className="ff-onboarding__role-key-text">
                            {r.role_key}
                          </span>
                        </label>
                      ))}
                    </div>
                  )}
                </fieldset>

                {/* Prefer the form's own validation/create error; fall back to
                    the slice's refresh failure (post-initial-load) surfaced as
                    the form-specific message — mirrors the now-removed
                    unreachable `.catch` in `refreshAgents`. */}
                {(() => {
                  const refreshFailed =
                    agentsError !== null && agentsFetchedAt !== null
                  const msg = agentError ?? (refreshFailed ? 'Failed to refresh agents' : null)
                  if (!msg) return null
                  return (
                    <p
                      id="onb-agent-error"
                      className="ff-onboarding__form-error"
                      role="alert"
                      aria-live="assertive"
                    >
                      {msg}
                    </p>
                  )
                })()}

                <button
                  type="submit"
                  className="ff-onboarding__add-btn"
                  disabled={creatingAgent || roles.length === 0}
                >
                  {creatingAgent ? 'Creating…' : 'Create Agent'}
                </button>
              </form>
            )}

            {/* Bottom nav */}
            <div className="ff-onboarding__actions">
              <button
                type="button"
                className="ff-onboarding__secondary-btn"
                onClick={goBack}
              >
                ← Back
              </button>
              <button
                type="button"
                className="ff-onboarding__primary-btn"
                disabled={!canProceedFromStep2}
                onClick={goNext}
              >
                Continue
              </button>
            </div>
          </div>
        )}

        {/* ── step 3: complete ──────────────────────────────── */}
        {step === 3 && (
          <div className="ff-onboarding__content">
            <h2 className="ff-onboarding__step-title">
              Step 3: Complete setup
            </h2>

            <div className="ff-onboarding__summary">
              <p>
                You've configured{' '}
                <strong>
                  {roles.length} role{roles.length !== 1 ? 's' : ''}
                </strong>{' '}
                and registered{' '}
                <strong>
                  {agents.length} agent{agents.length !== 1 ? 's' : ''}
                </strong>
                .
              </p>
              <p>
                Once you finish setup, you'll be taken to the Jobs dashboard
                where you can start publishing and tracking handoff jobs.
              </p>
            </div>

            {finishError && (
              <p
                className="ff-onboarding__form-error"
                role="alert"
                aria-live="assertive"
              >
                {finishError}
              </p>
            )}

            <div className="ff-onboarding__actions">
              <button
                type="button"
                className="ff-onboarding__secondary-btn"
                onClick={goBack}
                disabled={finishing}
              >
                ← Back
              </button>
              <button
                type="button"
                className="ff-onboarding__primary-btn"
                onClick={handleFinishSetup}
                disabled={finishing}
              >
                {finishing ? 'Finishing…' : 'Finish Setup'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
