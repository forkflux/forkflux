import { useEffect, useState } from 'react'
import { Drawer } from '../../components/Drawer/Drawer'
import { formatDate, slugifyRoleKey } from '../../lib/jobs/jobs'
import { useRoles } from '../../store/hooks'
import { jobService } from '@job-service'
import type { Role } from '../../types/job.ts'
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

  // Edit-role form state (purely page-local UI state — stays here).
  const [editOpen, setEditOpen] = useState(false)
  const [editRole, setEditRole] = useState<Role | null>(null)
  const [editKey, setEditKey] = useState('')
  const [editLabel, setEditLabel] = useState('')
  const [editKeyTouched, setEditKeyTouched] = useState(false)
  const [updating, setUpdating] = useState(false)
  const [editError, setEditError] = useState<string | null>(null)

  // Delete-role confirmation state (purely page-local UI state — stays here).
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<Role | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

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

  /** Open the edit-role drawer, pre-populated with the role's values. */
  function openEditForm(role: Role) {
    setEditRole(role)
    setEditKey(role.role_key)
    setEditLabel(role.role_label)
    setEditKeyTouched(true)
    setEditError(null)
    setEditOpen(true)
  }

  /**
   * Handle changes to the edit-role label input. When the user has not
   * manually edited the role key, auto-suggest a slugified key from the
   * label — mirroring the create form's behavior.
   */
  function handleEditLabelChange(value: string) {
    setEditLabel(value)
    if (!editKeyTouched) {
      setEditKey(slugifyRoleKey(value))
    }
  }

  /** Handle manual edits to the edit-role key — stops auto-suggestion. */
  function handleEditKeyChange(value: string) {
    setEditKeyTouched(true)
    setEditKey(value)
  }

  /**
   * Submit the edit-role form. Validates that both fields are non-empty
   * before calling the API. On success, invalidates the roles cache so
   * the next render refetches, and closes the drawer. On error, displays
   * a user-friendly message.
   */
  async function handleEditSubmit(e: React.FormEvent) {
    e.preventDefault()

    if (!editRole) return

    const trimmedKey = editKey.trim()
    const trimmedLabel = editLabel.trim()

    if (!trimmedLabel) {
      setEditError('Please provide a role label.')
      return
    }
    if (!trimmedKey) {
      setEditError('Please provide a role key.')
      return
    }

    setUpdating(true)
    setEditError(null)

    try {
      await jobService.updateRole(editRole.id, trimmedKey, trimmedLabel)
      // Invalidate the shared cache + force a refetch so the updated
      // role shows up across RolesPage AND AgentsPage.
      invalidate()
      await fetch(true)
      setEditOpen(false)
      setEditRole(null)
    } catch (err) {
      setEditError(
        err instanceof Error
          ? err.message
          : 'Failed to update role. Please try again.',
      )
    } finally {
      setUpdating(false)
    }
  }

  /** Open the delete-confirmation drawer for the given role. */
  function openDeleteConfirm(role: Role) {
    setDeleteTarget(role)
    setDeleteError(null)
    setDeleteOpen(true)
  }

  /**
   * Confirm the role deletion. Calls the API to delete the role, then
   * invalidates the roles cache and refetches so the removed role
   * disappears across RolesPage AND AgentsPage. On error, displays a
   * user-friendly message inside the confirmation drawer.
   */
  async function handleDeleteConfirm() {
    if (!deleteTarget) return

    setDeleting(true)
    setDeleteError(null)

    try {
      await jobService.deleteRole(deleteTarget.id)
      // Invalidate the shared cache + force a refetch so the deleted
      // role is removed across RolesPage AND AgentsPage.
      invalidate()
      await fetch(true)
      setDeleteOpen(false)
      setDeleteTarget(null)
    } catch (err) {
      setDeleteError(
        err instanceof Error
          ? err.message
          : 'Failed to delete role. Please try again.',
      )
    } finally {
      setDeleting(false)
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
                <th className="ff-roles__th ff-roles__th--actions">Actions</th>
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
                  <td className="ff-roles__td ff-roles__td--actions">
                    <button
                      type="button"
                      className="ff-roles__edit-btn"
                      onClick={() => openEditForm(role)}
                      aria-label={`Edit role ${role.role_label}`}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      className="ff-roles__delete-btn"
                      onClick={() => openDeleteConfirm(role)}
                      aria-label={`Delete role ${role.role_label}`}
                      disabled={deleting && deleteTarget?.id === role.id}
                    >
                      Delete
                    </button>
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

      {/* Edit role form drawer */}
      <Drawer
        open={editOpen}
        onClose={() => setEditOpen(false)}
        title="Edit Role"
        width="500px"
      >
        <form className="ff-roles__form" onSubmit={handleEditSubmit} noValidate>
          <p className="ff-roles__form-desc">
            Update this target role's <strong>key</strong> and
            <strong> label</strong>. The <strong>role key</strong> is the
            stable identifier used in API calls; the <strong>label</strong>
            is the human-readable display name.
          </p>

          <label className="ff-roles__label" htmlFor="edit-role-label">
            Role Label <span className="ff-roles__required">*</span>
          </label>
          <input
            id="edit-role-label"
            type="text"
            className="ff-roles__input"
            value={editLabel}
            onChange={(e) => handleEditLabelChange(e.target.value)}
            placeholder="e.g. Frontend Engineer"
            disabled={updating}
            required
            aria-describedby={editError ? 'edit-role-form-error' : undefined}
            aria-invalid={editError ? true : undefined}
            autoFocus
          />

          <label className="ff-roles__label" htmlFor="edit-role-key">
            Role Key <span className="ff-roles__required">*</span>
          </label>
          <input
            id="edit-role-key"
            type="text"
            className="ff-roles__input ff-roles__input--mono"
            value={editKey}
            onChange={(e) => handleEditKeyChange(e.target.value)}
            placeholder="e.g. frontend_engineer"
            disabled={updating}
            required
            aria-describedby={editError ? 'edit-role-form-error' : undefined}
            aria-invalid={editError ? true : undefined}
          />
          {!editKeyTouched && editLabel && (
            <p className="ff-roles__hint">Auto-generated from label</p>
          )}

          {editError && (
            <p
              id="edit-role-form-error"
              className="ff-roles__form-error"
              role="alert"
              aria-live="assertive"
            >
              {editError}
            </p>
          )}

          <div className="ff-roles__form-actions">
            <button
              type="button"
              className="ff-roles__cancel-btn"
              onClick={() => setEditOpen(false)}
              disabled={updating}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="ff-roles__submit-btn"
              disabled={updating}
            >
              {updating ? 'Saving…' : 'Save Changes'}
            </button>
          </div>
        </form>
      </Drawer>

      {/*
        Delete role confirmation drawer. Reuses the same Drawer component
        as the create/edit forms for visual and behavioral consistency.
        Shows a warning with the role label and a danger-styled confirm
        button so the user must explicitly confirm the destructive action.
      */}
      <Drawer
        open={deleteOpen}
        onClose={() => setDeleteOpen(false)}
        title="Delete Role"
        width="500px"
      >
        <div className="ff-roles__confirm">
          <p className="ff-roles__confirm-text">
            Are you sure you want to delete the role{' '}
            <strong className="ff-roles__confirm-role">
              {deleteTarget?.role_label}
            </strong>{' '}
            (<code className="ff-roles__confirm-code">{deleteTarget?.role_key}</code>)?
          </p>
          <p className="ff-roles__confirm-warning">
            This action cannot be undone. Jobs already assigned to this
            role will retain their assignment, but no new jobs can be
            routed to it.
          </p>

          {deleteError && (
            <p
              className="ff-roles__form-error"
              role="alert"
              aria-live="assertive"
            >
              {deleteError}
            </p>
          )}

          <div className="ff-roles__form-actions">
            <button
              type="button"
              className="ff-roles__cancel-btn"
              onClick={() => setDeleteOpen(false)}
              disabled={deleting}
            >
              Cancel
            </button>
            <button
              type="button"
              className="ff-roles__delete-confirm-btn"
              onClick={handleDeleteConfirm}
              disabled={deleting}
            >
              {deleting ? 'Deleting…' : 'Confirm Delete'}
            </button>
          </div>
        </div>
      </Drawer>
    </div>
  )
}
