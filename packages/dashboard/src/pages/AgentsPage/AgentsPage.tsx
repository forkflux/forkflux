import { useEffect, useRef, useState } from 'react'
import { Drawer } from '../../components/Drawer/Drawer'
import { formatDate } from '../../lib/jobs/jobs'
import { jobService } from '@job-service'
import { useRoles } from '../../store/hooks'
import { useAgents } from '../../store/hooks'
import type { CreateAgentResponse } from '../../types/job'
import './AgentsPage.scss'

export function AgentsPage() {
  // Agents + roles come from the shared store. Roles are reused with
  // RolesPage via the same `rolesSlice`, so switching tabs no longer triggers
  // a duplicate `fetchRoles`.
  const { items: agents, isLoading, error, fetch: fetchAgents } = useAgents()
  const { items: roles, fetch: fetchRoles } = useRoles()

  // Create-agent form state (purely page-local UI state — stays here).
  const [createOpen, setCreateOpen] = useState(false)
  const [agentLabel, setAgentLabel] = useState('')
  const [toolFamily, setToolFamily] = useState('')
  const [selectedRoleIds, setSelectedRoleIds] = useState<number[]>([])
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)

  // Token success view state
  const [createdAgent, setCreatedAgent] = useState<CreateAgentResponse | null>(
    null,
  )
  const [copied, setCopied] = useState(false)
  const [copyFailed, setCopyFailed] = useState(false)
  const tokenInputRef = useRef<HTMLInputElement>(null)

  // Load agents + roles on mount via the shared store slices. Both slices
  // dedupe concurrent callers and cache fresh results.
  useEffect(() => {
    void fetchAgents()
    void fetchRoles()
  }, [fetchAgents, fetchRoles])

  /** Open the create-agent drawer and reset form state. */
  function openCreateForm() {
    setAgentLabel('')
    setToolFamily('')
    setSelectedRoleIds([])
    setCreateError(null)
    setCreatedAgent(null)
    setCopied(false)
    setCopyFailed(false)
    setCreateOpen(true)
  }

  /** Toggle a role ID in the selected set. */
  function toggleRole(roleId: number) {
    setSelectedRoleIds((prev) =>
      prev.includes(roleId)
        ? prev.filter((id) => id !== roleId)
        : [...prev, roleId],
    )
  }

  /**
   * Copy the API token to the clipboard. Falls back to selecting the token
   * input if the clipboard API is unavailable.
   */
  async function handleCopyToken() {
    if (!createdAgent) return
    try {
      await navigator.clipboard.writeText(createdAgent.api_token)
      setCopied(true)
      setCopyFailed(false)
    } catch {
      // Clipboard API may be unavailable (e.g. insecure context). Select
      // the token input so the user can copy manually with Cmd/Ctrl+C,
      // and show fallback guidance.
      setCopied(false)
      setCopyFailed(true)
      tokenInputRef.current?.select()
    }
  }

  /**
   * Submit the create-agent form. Validates that the label is non-empty and
   * at least one role is selected before calling the API. On success,
   * switches the drawer to the token-success view. On error, displays a
   * user-friendly message.
   */
  async function handleCreateSubmit(e: React.FormEvent) {
    e.preventDefault()

    const trimmedLabel = agentLabel.trim()

    if (!trimmedLabel) {
      setCreateError('Please provide an agent label.')
      return
    }
    if (selectedRoleIds.length === 0) {
      setCreateError('Please select at least one role.')
      return
    }

    setCreating(true)
    setCreateError(null)

    try {
      const result = await jobService.createAgent(
        trimmedLabel,
        toolFamily.trim() || null,
        selectedRoleIds,
      )
      setCreatedAgent(result)
      setCopied(false)
    } catch (err) {
      setCreateError(
        err instanceof Error
          ? err.message
          : 'Failed to create agent. Please try again.',
      )
    } finally {
      setCreating(false)
    }
  }

  /**
   * Close the drawer. If a token was just shown, force-refetch the agents
   * slice so the new agent appears in the table. Reset all form/token state.
   */
  function handleCloseDrawer() {
    setCreateOpen(false)
    if (createdAgent) {
      // Force a refetch bypassing the cache so the just-created agent shows up.
      void fetchAgents(true)
    }
    setCreatedAgent(null)
    setAgentLabel('')
    setToolFamily('')
    setSelectedRoleIds([])
    setCreateError(null)
    setCopied(false)
    setCopyFailed(false)
  }

  if (isLoading) {
    return <div className="ff-agents">Loading agents…</div>
  }

  if (error) {
    return <div className="ff-agents ff-agents--error">Error: {error}</div>
  }

  return (
    <div className="ff-agents">
      <div className="ff-agents__header">
        <h1>Agents</h1>
        <span className="ff-agents__count">{agents.length} total</span>
        <button
          type="button"
          className="ff-agents__add-btn"
          onClick={openCreateForm}
        >
          + New Agent
        </button>
      </div>

      {agents.length === 0 ? (
        <p className="ff-agents__empty">No agents have been registered yet.</p>
      ) : (
        <div className="ff-agents__table-wrap">
          <table className="ff-agents__table">
            <thead>
              <tr>
                <th className="ff-agents__th">Label</th>
                <th className="ff-agents__th">Roles</th>
                <th className="ff-agents__th">Tool Family</th>
                <th className="ff-agents__th">Created</th>
              </tr>
            </thead>
            <tbody>
              {agents.map((agent) => (
                <tr key={agent.id} className="ff-agents__row">
                  <td className="ff-agents__td ff-agents__td--mono">
                    {agent.agent_label}
                  </td>
                  <td className="ff-agents__td">
                    {agent.roles.length === 0 ? (
                      <span className="ff-agents__no-roles">—</span>
                    ) : (
                      <div className="ff-agents__badges">
                        {agent.roles.map((role) => (
                          <span
                            key={role.role_key}
                            className="ff-agents__badge"
                          >
                            {role.role_label}
                          </span>
                        ))}
                      </div>
                    )}
                  </td>
                  <td className="ff-agents__td ff-agents__td--muted">
                    {agent.tool_family ?? (
                      <span className="ff-agents__no-roles">—</span>
                    )}
                  </td>
                  <td className="ff-agents__td ff-agents__td--muted">
                    {formatDate(agent.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create agent form / token success drawer */}
      <Drawer
        open={createOpen}
        onClose={handleCloseDrawer}
        title={createdAgent ? 'Agent Created' : 'New Agent'}
        width="500px"
      >
        {createdAgent ? (
          <div className="ff-agents__token-view">
            <p className="ff-agents__token-warning" role="alert">
              <strong>⚠ Copy your API token now.</strong> It will not be shown
              again.
            </p>

            <label className="ff-agents__label" htmlFor="agent-token">
              API Token
            </label>
            <div className="ff-agents__token-box">
              <input
                ref={tokenInputRef}
                id="agent-token"
                type="text"
                className="ff-agents__token-input"
                value={createdAgent.api_token}
                readOnly
                onFocus={(e) => e.target.select()}
              />
              <button
                type="button"
                className="ff-agents__copy-btn"
                onClick={handleCopyToken}
              >
                {copied ? '✓ Copied' : 'Copy'}
              </button>
            </div>

            {copyFailed && (
              <p
                className="ff-agents__token-fallback"
                role="alert"
                aria-live="assertive"
              >
                Automatic copy failed. The token is selected — press
                Cmd/Ctrl+C to copy it manually.
              </p>
            )}

            <div className="ff-agents__token-summary">
              <p>
                <strong>Agent:</strong> {createdAgent.agent_label}
              </p>
              {createdAgent.tool_family && (
                <p>
                  <strong>Tool family:</strong> {createdAgent.tool_family}
                </p>
              )}
            </div>

            <div className="ff-agents__form-actions">
              <button
                type="button"
                className="ff-agents__done-btn"
                onClick={handleCloseDrawer}
              >
                Done
              </button>
            </div>
          </div>
        ) : (
          <form
            className="ff-agents__form"
            onSubmit={handleCreateSubmit}
            noValidate
          >
            <p className="ff-agents__form-desc">
              Register a new agent. The agent will receive an API token that
              is shown <strong>only once</strong> — copy it immediately after
              creation.
            </p>

            <label className="ff-agents__label" htmlFor="agent-label">
              Agent Label <span className="ff-agents__required">*</span>
            </label>
            <input
              id="agent-label"
              type="text"
              className="ff-agents__input"
              value={agentLabel}
              onChange={(e) => setAgentLabel(e.target.value)}
              placeholder="e.g. frontend-bot"
              disabled={creating}
              required
              aria-describedby={createError ? 'agent-form-error' : undefined}
              aria-invalid={createError ? true : undefined}
              autoFocus
            />

            <label className="ff-agents__label" htmlFor="agent-tool-family">
              Tool Family
            </label>
            <input
              id="agent-tool-family"
              type="text"
              className="ff-agents__input"
              value={toolFamily}
              onChange={(e) => setToolFamily(e.target.value)}
              placeholder="e.g. playwright (optional)"
              disabled={creating}
            />

            <label className="ff-agents__label">
              Target Roles <span className="ff-agents__required">*</span>
            </label>
            {roles.length === 0 ? (
              <p className="ff-agents__hint">
                No roles available. Create a role first.
              </p>
            ) : (
              <div className="ff-agents__role-list">
                {roles.map((role) => (
                  <label
                    key={role.id}
                    className="ff-agents__role-option"
                  >
                    <input
                      type="checkbox"
                      className="ff-agents__checkbox"
                      checked={selectedRoleIds.includes(role.id)}
                      onChange={() => toggleRole(role.id)}
                      disabled={creating}
                    />
                    <span className="ff-agents__role-label-text">
                      {role.role_label}
                    </span>
                    <span className="ff-agents__role-key-text">
                      {role.role_key}
                    </span>
                  </label>
                ))}
              </div>
            )}

            {createError && (
              <p
                id="agent-form-error"
                className="ff-agents__form-error"
                role="alert"
                aria-live="assertive"
              >
                {createError}
              </p>
            )}

            <div className="ff-agents__form-actions">
              <button
                type="button"
                className="ff-agents__cancel-btn"
                onClick={handleCloseDrawer}
                disabled={creating}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="ff-agents__submit-btn"
                disabled={creating || roles.length === 0}
              >
                {creating ? 'Creating…' : 'Create Agent'}
              </button>
            </div>
          </form>
        )}
      </Drawer>
    </div>
  )
}
