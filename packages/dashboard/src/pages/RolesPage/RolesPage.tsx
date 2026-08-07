import { useEffect, useState } from 'react'
import { Drawer } from '../../components/Drawer/Drawer'
import { formatDate, slugifyRoleKey } from '../../lib/jobs/jobs'
import { useRoles } from '../../store/hooks'
import { jobService } from '@job-service'
import './RolesPage.scss'

export function RolesPage() {
  const { items: roles, isLoading, error, fetch, invalidate } = useRoles()

  // Create-role form state (purely page-local UI state — stays here).
  const [createOpen, setCreateOpen] = useState(false)
  const [roleKey, setRoleKey] = useState('')
  const [roleLabel, setRoleLabel] = useState('')
  const [roleKeyTouched, setRoleKeyTouched] = useState(false)
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)

  // Load roles on mount via the shared store slice. The slice dedupes
  // concurrent callers and caches fresh results, so visiting RolesPage and
  // then AgentsPage fetches roles once, not twice.
  useEffect(() => {
    void fetch()
  }, [fetch])

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
   * before calling the API. On success, invalidates the roles cache so the
   * next render refetches, and closes the drawer. On error, displays a
   * user-friendly message.
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
      // Invalidate the shared cache + force a refetch so the new role shows
      // up across RolesPage AND AgentsPage (which reuse the same slice).
      invalidate()
      await fetch(true)
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

  if (isLoading) {
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
