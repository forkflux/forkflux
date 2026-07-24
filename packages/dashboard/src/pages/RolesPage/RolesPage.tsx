import { useEffect, useState } from 'react'
import { Drawer } from '../../components/Drawer/Drawer'
import { formatDate, slugifyRoleKey } from '../../lib/jobs/jobs'
import { jobService } from '../../services/jobService'
import type { Role } from '../../types/job'
import './RolesPage.scss'

export function RolesPage() {
  const [roles, setRoles] = useState<Role[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Create-role form state
  const [createOpen, setCreateOpen] = useState(false)
  const [roleKey, setRoleKey] = useState('')
  const [roleLabel, setRoleLabel] = useState('')
  const [roleKeyTouched, setRoleKeyTouched] = useState(false)
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loading flag before async fetch
    setLoading(true)
    jobService
      .fetchRoles()
      .then((data) => {
        if (cancelled) return
        setRoles(data)
        setError(null)
      })
      .catch((err) => {
        if (cancelled) return
        setError(err instanceof Error ? err.message : 'Failed to load roles')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  /**
   * Refresh the roles list from the data source. Used after a successful
   * create to reflect the new role without a full page reload.
   */
  function refreshRoles() {
    return jobService
      .fetchRoles()
      .then((data) => {
        setRoles(data)
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Failed to load roles')
      })
  }

  /** Open the create-role drawer and reset form state. */
  function openCreateForm() {
    setRoleKey('')
    setRoleLabel('')
    setRoleKeyTouched(false)
    setCreateError(null)
    setCreateOpen(true)
  }

  /**
   * Handle changes to the role label input. When the user has not manually
   * edited the role key, auto-suggest a slugified key from the label.
   */
  function handleLabelChange(value: string) {
    setRoleLabel(value)
    if (!roleKeyTouched) {
      setRoleKey(slugifyRoleKey(value))
    }
  }

  /** Handle manual edits to the role key — stops auto-suggestion. */
  function handleKeyChange(value: string) {
    setRoleKeyTouched(true)
    setRoleKey(value)
  }

  /**
   * Submit the create-role form. Validates that both fields are non-empty
   * before calling the API. On success, refreshes the roles list and closes
   * the drawer. On error, displays a user-friendly message.
   */
  async function handleCreateSubmit(e: React.FormEvent) {
    e.preventDefault()

    const trimmedKey = roleKey.trim()
    const trimmedLabel = roleLabel.trim()

    if (!trimmedLabel) {
      setCreateError('Please provide a role label.')
      return
    }
    if (!trimmedKey) {
      setCreateError('Please provide a role key.')
      return
    }

    setCreating(true)
    setCreateError(null)

    try {
      await jobService.createRole(trimmedKey, trimmedLabel)
      await refreshRoles()
      setCreateOpen(false)
      setRoleKey('')
      setRoleLabel('')
      setRoleKeyTouched(false)
    } catch (err) {
      setCreateError(
        err instanceof Error
          ? err.message
          : 'Failed to create role. Please try again.',
      )
    } finally {
      setCreating(false)
    }
  }

  if (loading) {
    return <div className="ff-roles">Loading roles…</div>
  }

  if (error) {
    return <div className="ff-roles ff-roles--error">Error: {error}</div>
  }

  return (
    <div className="ff-roles">
      <div className="ff-roles__header">
        <h1>Roles</h1>
        <span className="ff-roles__count">{roles.length} total</span>
        <button
          type="button"
          className="ff-roles__add-btn"
          onClick={openCreateForm}
        >
          + New Role
        </button>
      </div>

      {roles.length === 0 ? (
        <p className="ff-roles__empty">No roles have been created yet.</p>
      ) : (
        <div className="ff-roles__table-wrap">
          <table className="ff-roles__table">
            <thead>
              <tr>
                <th className="ff-roles__th">Key</th>
                <th className="ff-roles__th">Label</th>
                <th className="ff-roles__th">Created</th>
              </tr>
            </thead>
            <tbody>
              {roles.map((role) => (
                <tr key={role.id} className="ff-roles__row">
                  <td className="ff-roles__td ff-roles__td--mono">
                    {role.role_key}
                  </td>
                  <td className="ff-roles__td">{role.role_label}</td>
                  <td className="ff-roles__td ff-roles__td--muted">
                    {formatDate(role.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create role form drawer */}
      <Drawer
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title="New Role"
        width="500px"
      >
        <form className="ff-roles__form" onSubmit={handleCreateSubmit} noValidate>
          <p className="ff-roles__form-desc">
            Create a new target role. The <strong>role key</strong> is the
            stable identifier used in API calls; the <strong>label</strong> is
            the human-readable display name.
          </p>

          <label className="ff-roles__label" htmlFor="role-label">
            Role Label <span className="ff-roles__required">*</span>
          </label>
          <input
            id="role-label"
            type="text"
            className="ff-roles__input"
            value={roleLabel}
            onChange={(e) => handleLabelChange(e.target.value)}
            placeholder="e.g. Frontend Engineer"
            disabled={creating}
            required
            aria-describedby={createError ? 'role-form-error' : undefined}
            aria-invalid={createError ? true : undefined}
            autoFocus
          />

          <label className="ff-roles__label" htmlFor="role-key">
            Role Key <span className="ff-roles__required">*</span>
          </label>
          <input
            id="role-key"
            type="text"
            className="ff-roles__input ff-roles__input--mono"
            value={roleKey}
            onChange={(e) => handleKeyChange(e.target.value)}
            placeholder="e.g. frontend_engineer"
            disabled={creating}
            required
            aria-describedby={createError ? 'role-form-error' : undefined}
            aria-invalid={createError ? true : undefined}
          />
          {!roleKeyTouched && roleLabel && (
            <p className="ff-roles__hint">Auto-generated from label</p>
          )}

          {createError && (
            <p
              id="role-form-error"
              className="ff-roles__form-error"
              role="alert"
              aria-live="assertive"
            >
              {createError}
            </p>
          )}

          <div className="ff-roles__form-actions">
            <button
              type="button"
              className="ff-roles__cancel-btn"
              onClick={() => setCreateOpen(false)}
              disabled={creating}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="ff-roles__submit-btn"
              disabled={creating}
            >
              {creating ? 'Creating…' : 'Create Role'}
            </button>
          </div>
        </form>
      </Drawer>
    </div>
  )
}
