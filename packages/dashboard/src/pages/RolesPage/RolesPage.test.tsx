import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import { RolesPage } from './RolesPage'
import { renderWithRouter, createMockRole } from '../../test/utils'

// Use vi.hoisted so the mock service is created before the hoisted vi.mock
// factory runs.
const { mockService } = vi.hoisted(() => {
  const service = {
    fetchRoles: vi.fn(),
    createRole: vi.fn(),
  }
  return { mockService: service }
})

vi.mock('@job-service', () => ({
  jobService: mockService,
}))

const fetchRolesMock = vi.mocked(mockService.fetchRoles)
const createRoleMock = vi.mocked(mockService.createRole)

describe('RolesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    fetchRolesMock.mockResolvedValue([])
    createRoleMock.mockResolvedValue(createMockRole())
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
})
