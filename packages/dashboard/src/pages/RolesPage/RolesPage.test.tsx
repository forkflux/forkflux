import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { screen, waitFor, fireEvent, within } from '@testing-library/react'
import { RolesPage } from './RolesPage'
import { renderWithRouter, createMockRole } from '../../test/utils'
import { resetStore } from '../../store/index'
import '@testing-library/jest-dom/vitest'

// Use vi.hoisted so the mock service is created before the hoisted vi.mock
// factory runs.
const { mockService } = vi.hoisted(() => {
  const service = {
    fetchRoles: vi.fn(),
    createRole: vi.fn(),
    updateRole: vi.fn(),
    deleteRole: vi.fn(),
  }
  return { mockService: service }
})

vi.mock('@job-service', () => ({
  jobService: mockService,
}))

const fetchRolesMock = vi.mocked(mockService.fetchRoles)
const createRoleMock = vi.mocked(mockService.createRole)
const updateRoleMock = vi.mocked(mockService.updateRole)
const deleteRoleMock = vi.mocked(mockService.deleteRole)

describe('RolesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset the shared Zustand store so a fresh `fetchedAt` from a previous
    // test can't short-circuit this test's `fetch()` via the cache-skip path.
    resetStore()
    fetchRolesMock.mockResolvedValue([])
    createRoleMock.mockResolvedValue(createMockRole())
    updateRoleMock.mockResolvedValue(createMockRole())
    deleteRoleMock.mockResolvedValue(undefined)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('loading state', () => {
    it('shows loading message while fetching', () => {
      fetchRolesMock.mockReturnValue(new Promise(() => {}))
      renderWithRouter(<RolesPage />)
      expect(screen.getByText('Loading roles…')).toBeInTheDocument()
    })
  })

  describe('error state', () => {
    it('shows error message when fetchRoles rejects', async () => {
      fetchRolesMock.mockRejectedValue(new Error('Network error'))
      renderWithRouter(<RolesPage />)
      await waitFor(() => {
        expect(screen.getByText(/Error: Network error/)).toBeInTheDocument()
      })
    })

    it('shows generic error for non-Error rejections', async () => {
      fetchRolesMock.mockRejectedValue('string error')
      renderWithRouter(<RolesPage />)
      await waitFor(() => {
        expect(
          screen.getByText(/Error: Failed to load roles/),
        ).toBeInTheDocument()
      })
    })
  })

  describe('empty state', () => {
    it('shows empty message when no roles exist', async () => {
      fetchRolesMock.mockResolvedValue([])
      renderWithRouter(<RolesPage />)
      await waitFor(() => {
        expect(
          screen.getByText(/No roles have been created yet/),
        ).toBeInTheDocument()
      })
    })
  })

  describe('data rendering', () => {
    it('renders role rows with key, label, and created date', async () => {
      fetchRolesMock.mockResolvedValue([
        createMockRole({
          id: 1,
          role_key: 'frontend',
          role_label: 'Frontend Engineer',
          created_at: '2026-07-16T10:00:00Z',
        }),
        createMockRole({
          id: 2,
          role_key: 'backend',
          role_label: 'Backend Engineer',
          created_at: '2026-07-16T10:00:00Z',
        }),
      ])
      renderWithRouter(<RolesPage />)
      await waitFor(() => {
        expect(screen.getByText('frontend')).toBeInTheDocument()
        expect(screen.getByText('Frontend Engineer')).toBeInTheDocument()
        expect(screen.getByText('backend')).toBeInTheDocument()
        expect(screen.getByText('Backend Engineer')).toBeInTheDocument()
      })
    })

    it('shows the total count', async () => {
      fetchRolesMock.mockResolvedValue([
        createMockRole({ id: 1 }),
        createMockRole({ id: 2 }),
        createMockRole({ id: 3 }),
      ])
      renderWithRouter(<RolesPage />)
      await waitFor(() => {
        expect(screen.getByText('3 total')).toBeInTheDocument()
      })
    })
  })

  describe('create role form', () => {
    it('shows the New Role button', async () => {
      fetchRolesMock.mockResolvedValue([])
      renderWithRouter(<RolesPage />)
      await waitFor(() => {
        expect(screen.getByText('+ New Role')).toBeInTheDocument()
      })
    })

    it('opens the form drawer when New Role is clicked', async () => {
      fetchRolesMock.mockResolvedValue([])
      renderWithRouter(<RolesPage />)
      await waitFor(() => {
        expect(screen.getByText('+ New Role')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('+ New Role'))

      await waitFor(() => {
        expect(screen.getByText('New Role')).toBeInTheDocument()
        expect(screen.getByPlaceholderText('e.g. Frontend Engineer')).toBeInTheDocument()
        expect(screen.getByPlaceholderText('e.g. frontend_engineer')).toBeInTheDocument()
      })
    })

    it('auto-suggests role key from label via slugify', async () => {
      fetchRolesMock.mockResolvedValue([])
      renderWithRouter(<RolesPage />)
      await waitFor(() => {
        expect(screen.getByText('+ New Role')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('+ New Role'))
      await waitFor(() => {
        expect(screen.getByPlaceholderText('e.g. Frontend Engineer')).toBeInTheDocument()
      })

      const labelInput = screen.getByPlaceholderText('e.g. Frontend Engineer')
      fireEvent.change(labelInput, { target: { value: 'DevOps Engineer' } })

      const keyInput = screen.getByPlaceholderText('e.g. frontend_engineer') as HTMLInputElement
      expect(keyInput.value).toBe('devops_engineer')
    })

    it('stops auto-suggesting when role key is manually edited', async () => {
      fetchRolesMock.mockResolvedValue([])
      renderWithRouter(<RolesPage />)
      await waitFor(() => {
        expect(screen.getByText('+ New Role')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('+ New Role'))
      await waitFor(() => {
        expect(screen.getByPlaceholderText('e.g. Frontend Engineer')).toBeInTheDocument()
      })

      const labelInput = screen.getByPlaceholderText('e.g. Frontend Engineer')
      const keyInput = screen.getByPlaceholderText('e.g. frontend_engineer') as HTMLInputElement

      // Type a label — key auto-suggests
      fireEvent.change(labelInput, { target: { value: 'QA Tester' } })
      expect(keyInput.value).toBe('qa_tester')

      // Manually edit the key
      fireEvent.change(keyInput, { target: { value: 'custom_key' } })
      expect(keyInput.value).toBe('custom_key')

      // Change the label again — key should NOT change
      fireEvent.change(labelInput, { target: { value: 'Another Role' } })
      expect(keyInput.value).toBe('custom_key')
    })

    it('shows validation error when label is empty', async () => {
      fetchRolesMock.mockResolvedValue([])
      renderWithRouter(<RolesPage />)
      await waitFor(() => {
        expect(screen.getByText('+ New Role')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('+ New Role'))
      await waitFor(() => {
        expect(screen.getByText('Create Role')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('Create Role'))

      await waitFor(() => {
        expect(screen.getByText('Please provide a role label.')).toBeInTheDocument()
      })
      expect(createRoleMock).not.toHaveBeenCalled()
    })

    it('creates a role and refreshes the list on success', async () => {
      fetchRolesMock.mockResolvedValueOnce([])
      fetchRolesMock.mockResolvedValueOnce([
        createMockRole({ id: 1, role_key: 'qa', role_label: 'QA Tester' }),
      ])
      createRoleMock.mockResolvedValue(
        createMockRole({ id: 1, role_key: 'qa', role_label: 'QA Tester' }),
      )

      renderWithRouter(<RolesPage />)
      await waitFor(() => {
        expect(screen.getByText('+ New Role')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('+ New Role'))
      await waitFor(() => {
        expect(screen.getByPlaceholderText('e.g. Frontend Engineer')).toBeInTheDocument()
      })

      const labelInput = screen.getByPlaceholderText('e.g. Frontend Engineer')
      fireEvent.change(labelInput, { target: { value: 'QA Tester' } })

      fireEvent.click(screen.getByText('Create Role'))

      await waitFor(() => {
        expect(createRoleMock).toHaveBeenCalledWith('qa_tester', 'QA Tester')
      })

      // fetchRoles should be called twice: initial load + refresh after create
      await waitFor(() => {
        expect(fetchRolesMock).toHaveBeenCalledTimes(2)
      })

      // The new role should appear in the list
      await waitFor(() => {
        expect(screen.getByText('QA Tester')).toBeInTheDocument()
      })
    })

    it('shows error message when createRole rejects', async () => {
      fetchRolesMock.mockResolvedValue([])
      createRoleMock.mockRejectedValue(
        new Error('A role with the key "frontend" already exists.'),
      )

      renderWithRouter(<RolesPage />)
      await waitFor(() => {
        expect(screen.getByText('+ New Role')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('+ New Role'))
      await waitFor(() => {
        expect(screen.getByPlaceholderText('e.g. Frontend Engineer')).toBeInTheDocument()
      })

      const labelInput = screen.getByPlaceholderText('e.g. Frontend Engineer')
      fireEvent.change(labelInput, { target: { value: 'Frontend Engineer' } })

      fireEvent.click(screen.getByText('Create Role'))

      await waitFor(() => {
        expect(
          screen.getByText('A role with the key "frontend" already exists.'),
        ).toBeInTheDocument()
      })
    })

    it('closes the drawer when Cancel is clicked', async () => {
      fetchRolesMock.mockResolvedValue([])
      renderWithRouter(<RolesPage />)
      await waitFor(() => {
        expect(screen.getByText('+ New Role')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('+ New Role'))
      await waitFor(() => {
        expect(screen.getByText('Create Role')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('Cancel'))

      await waitFor(() => {
        expect(screen.queryByText('Create Role')).not.toBeInTheDocument()
      })
    })
  })

  describe('edit role form', () => {
    it('renders an Edit button per role row', async () => {
      fetchRolesMock.mockResolvedValue([
        createMockRole({
          id: 1,
          role_key: 'frontend',
          role_label: 'Frontend Engineer',
        }),
      ])
      renderWithRouter(<RolesPage />)
      await waitFor(() => {
        expect(screen.getByText('frontend')).toBeInTheDocument()
      })

      expect(screen.getByText('Edit')).toBeInTheDocument()
      expect(screen.getByLabelText('Edit role Frontend Engineer')).toBeInTheDocument()
    })

    it('opens the edit drawer pre-populated when Edit is clicked', async () => {
      fetchRolesMock.mockResolvedValue([
        createMockRole({
          id: 1,
          role_key: 'frontend',
          role_label: 'Frontend Engineer',
        }),
      ])
      renderWithRouter(<RolesPage />)
      await waitFor(() => {
        expect(screen.getByText('Edit')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('Edit'))

      // Drawer open with title and pre-populated inputs.
      await waitFor(() => {
        expect(screen.getByText('Edit Role')).toBeInTheDocument()
        expect(
          screen.getByPlaceholderText('e.g. Frontend Engineer'),
        ).toBeInTheDocument()
        expect(
          screen.getByPlaceholderText('e.g. frontend_engineer'),
        ).toBeInTheDocument()
      })
      expect(
        (screen.getByPlaceholderText('e.g. Frontend Engineer') as HTMLInputElement).value,
      ).toBe('Frontend Engineer')
      expect(
        (screen.getByPlaceholderText('e.g. frontend_engineer') as HTMLInputElement).value,
      ).toBe('frontend')
    })

    it('updates a role and refreshes the list on success', async () => {
      fetchRolesMock.mockResolvedValueOnce([
        createMockRole({
          id: 1,
          role_key: 'frontend',
          role_label: 'Frontend Engineer',
        }),
      ])
      fetchRolesMock.mockResolvedValueOnce([
        createMockRole({
          id: 1,
          role_key: 'frontend',
          role_label: 'Frontend Specialist',
        }),
      ])
      updateRoleMock.mockResolvedValue(
        createMockRole({
          id: 1,
          role_key: 'frontend',
          role_label: 'Frontend Specialist',
        }),
      )

      renderWithRouter(<RolesPage />)
      await waitFor(() => {
        expect(screen.getByText('Edit')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('Edit'))
      await waitFor(() => {
        expect(screen.getByText('Save Changes')).toBeInTheDocument()
      })

      // Change the label.
      const labelInput = screen.getByPlaceholderText('e.g. Frontend Engineer')
      fireEvent.change(labelInput, { target: { value: 'Frontend Specialist' } })

      fireEvent.click(screen.getByText('Save Changes'))

      await waitFor(() => {
        expect(updateRoleMock).toHaveBeenCalledWith(1, 'frontend', 'Frontend Specialist')
      })

      // fetchRoles should be called twice: initial load + refresh after edit.
      await waitFor(() => {
        expect(fetchRolesMock).toHaveBeenCalledTimes(2)
      })

      // The updated label appears in the list.
      await waitFor(() => {
        expect(screen.getByText('Frontend Specialist')).toBeInTheDocument()
      })
    })

    it('shows validation error when label is empty on edit', async () => {
      fetchRolesMock.mockResolvedValue([
        createMockRole({
          id: 1,
          role_key: 'frontend',
          role_label: 'Frontend Engineer',
        }),
      ])
      renderWithRouter(<RolesPage />)
      await waitFor(() => {
        expect(screen.getByText('Edit')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('Edit'))
      await waitFor(() => {
        expect(screen.getByText('Save Changes')).toBeInTheDocument()
      })

      // Clear the label.
      const labelInput = screen.getByPlaceholderText('e.g. Frontend Engineer')
      fireEvent.change(labelInput, { target: { value: '' } })

      fireEvent.click(screen.getByText('Save Changes'))

      await waitFor(() => {
        expect(screen.getByText('Please provide a role label.')).toBeInTheDocument()
      })
      expect(updateRoleMock).not.toHaveBeenCalled()
    })

    it('shows error message when updateRole rejects', async () => {
      fetchRolesMock.mockResolvedValue([
        createMockRole({
          id: 1,
          role_key: 'frontend',
          role_label: 'Frontend Engineer',
        }),
      ])
      updateRoleMock.mockRejectedValue(
        new Error('A role with the key "backend" already exists.'),
      )

      renderWithRouter(<RolesPage />)
      await waitFor(() => {
        expect(screen.getByText('Edit')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('Edit'))
      await waitFor(() => {
        expect(screen.getByPlaceholderText('e.g. Frontend Engineer')).toBeInTheDocument()
      })

      // Change the key to one that conflicts.
      const keyInput = screen.getByPlaceholderText('e.g. frontend_engineer')
      fireEvent.change(keyInput, { target: { value: 'backend' } })

      fireEvent.click(screen.getByText('Save Changes'))

      await waitFor(() => {
        expect(
          screen.getByText('A role with the key "backend" already exists.'),
        ).toBeInTheDocument()
      })
    })

    it('closes the edit drawer when Cancel is clicked', async () => {
      fetchRolesMock.mockResolvedValue([
        createMockRole({
          id: 1,
          role_key: 'frontend',
          role_label: 'Frontend Engineer',
        }),
      ])
      renderWithRouter(<RolesPage />)
      await waitFor(() => {
        expect(screen.getByText('Edit')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('Edit'))
      await waitFor(() => {
        expect(screen.getByText('Save Changes')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('Cancel'))

      await waitFor(() => {
        expect(screen.queryByText('Save Changes')).not.toBeInTheDocument()
      })
    })

    it('does not auto-suggest the key from the label on edit (key is pre-populated)', async () => {
      fetchRolesMock.mockResolvedValue([
        createMockRole({
          id: 1,
          role_key: 'frontend',
          role_label: 'Frontend Engineer',
        }),
      ])
      renderWithRouter(<RolesPage />)
      await waitFor(() => {
        expect(screen.getByText('Edit')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('Edit'))
      await waitFor(() => {
        expect(screen.getByPlaceholderText('e.g. Frontend Engineer')).toBeInTheDocument()
      })

      const labelInput = screen.getByPlaceholderText('e.g. Frontend Engineer')
      const keyInput = screen.getByPlaceholderText('e.g. frontend_engineer') as HTMLInputElement

      // Change the label — key should NOT auto-suggest (key is pre-populated,
      // `editKeyTouched` starts true for pre-existing roles).
      fireEvent.change(labelInput, { target: { value: 'Backend Engineer' } })
      expect(keyInput.value).toBe('frontend')
    })
  })

  describe('delete role confirmation', () => {
    it('renders a Delete button per role row', async () => {
      fetchRolesMock.mockResolvedValue([
        createMockRole({
          id: 1,
          role_key: 'frontend',
          role_label: 'Frontend Engineer',
        }),
      ])
      renderWithRouter(<RolesPage />)
      await waitFor(() => {
        expect(screen.getByText('Edit')).toBeInTheDocument()
      })

      expect(screen.getByText('Delete')).toBeInTheDocument()
      expect(
        screen.getByLabelText('Delete role Frontend Engineer'),
      ).toBeInTheDocument()
    })

    it('opens the confirmation drawer when Delete is clicked', async () => {
      fetchRolesMock.mockResolvedValue([
        createMockRole({
          id: 1,
          role_key: 'frontend',
          role_label: 'Frontend Engineer',
        }),
      ])
      renderWithRouter(<RolesPage />)
      await waitFor(() => {
        expect(screen.getByText('Delete')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('Delete'))

      await waitFor(() => {
        // The confirmation sentence is split across a <p> parent and
        // nested <strong>/<code> children, so an exact-string getByText
        // matches none of them. A substring regex matcher is the
        // correct way to assert on the leading fragment.
        expect(
          screen.getByText(/Are you sure you want to delete/),
        ).toBeInTheDocument()
      })

      // The role label "Frontend Engineer" appears both in the table's
      // label cell AND inside the delete-confirmation drawer's <strong>.
      // Scope the assertion to the Delete Role dialog so getByText finds
      // exactly one element and does not error on the duplicate.
      const deleteDialog = await screen.findByRole('dialog', {
        name: 'Delete Role',
      })
      expect(
        within(deleteDialog).getByText('Frontend Engineer'),
      ).toBeInTheDocument()
    })

    it('deletes a role and refreshes the list on success', async () => {
      fetchRolesMock.mockResolvedValueOnce([
        createMockRole({
          id: 1,
          role_key: 'frontend',
          role_label: 'Frontend Engineer',
        }),
      ])
      fetchRolesMock.mockResolvedValueOnce([])

      renderWithRouter(<RolesPage />)
      await waitFor(() => {
        expect(screen.getByText('Delete')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('Delete'))

      await waitFor(() => {
        // The confirmation drawer shows the confirm button with unique text.
        expect(screen.getByText('Confirm Delete')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('Confirm Delete'))

      await waitFor(() => {
        expect(deleteRoleMock).toHaveBeenCalledWith(1)
      })

      // fetchRoles should be called twice: initial load + refresh after delete.
      await waitFor(() => {
        expect(fetchRolesMock).toHaveBeenCalledTimes(2)
      })
    })

    it('shows error message when deleteRole rejects', async () => {
      fetchRolesMock.mockResolvedValue([
        createMockRole({
          id: 1,
          role_key: 'frontend',
          role_label: 'Frontend Engineer',
        }),
      ])
      deleteRoleMock.mockRejectedValue(
        new Error('This role no longer exists. Please refresh and try again.'),
      )

      renderWithRouter(<RolesPage />)
      await waitFor(() => {
        expect(screen.getByText('Delete')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('Delete'))

      await waitFor(() => {
        expect(screen.getByText('Confirm Delete')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('Confirm Delete'))

      await waitFor(() => {
        expect(
          screen.getByText('This role no longer exists. Please refresh and try again.'),
        ).toBeInTheDocument()
      })
    })

    it('closes the confirmation drawer when Cancel is clicked', async () => {
      fetchRolesMock.mockResolvedValue([
        createMockRole({
          id: 1,
          role_key: 'frontend',
          role_label: 'Frontend Engineer',
        }),
      ])
      renderWithRouter(<RolesPage />)
      await waitFor(() => {
        expect(screen.getByText('Delete')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('Delete'))

      await waitFor(() => {
        expect(screen.getByText('Confirm Delete')).toBeInTheDocument()
      })

      // Click Cancel inside the confirmation drawer.
      fireEvent.click(screen.getByText('Cancel'))

      await waitFor(() => {
        // The confirm button should be gone after cancellation.
        expect(screen.queryByText('Confirm Delete')).not.toBeInTheDocument()
        // But the row's Delete button should still be there.
        expect(screen.getByText('Delete')).toBeInTheDocument()
      })

      expect(deleteRoleMock).not.toHaveBeenCalled()
    })
  })
})
