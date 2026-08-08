import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import { AgentsPage } from './AgentsPage'
import {
  renderWithRouter,
  createMockAgent,
  createMockRole,
  createMockCreateAgentResponse,
} from '../../test/utils'
import { resetStore } from '../../store/index'
import '@testing-library/jest-dom/vitest'

// Use vi.hoisted so the mock service is created before the hoisted vi.mock
// factory runs.
const { mockService } = vi.hoisted(() => {
  const service = {
    fetchAgents: vi.fn(),
    fetchRoles: vi.fn(),
    createAgent: vi.fn(),
  }
  return { mockService: service }
})

vi.mock('@job-service', () => ({
  jobService: mockService,
}))

const fetchAgentsMock = vi.mocked(mockService.fetchAgents)
const fetchRolesMock = vi.mocked(mockService.fetchRoles)
const createAgentMock = vi.mocked(mockService.createAgent)

const MOCK_ROLES = [
  createMockRole({ id: 1, role_key: 'frontend', role_label: 'Frontend Engineer' }),
  createMockRole({ id: 2, role_key: 'backend', role_label: 'Backend Engineer' }),
]

describe('AgentsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset the shared Zustand store so a fresh `fetchedAt` from a previous
    // test can't short-circuit this test's `fetch()` via the cache-skip path.
    resetStore()
    fetchAgentsMock.mockResolvedValue([])
    fetchRolesMock.mockResolvedValue(MOCK_ROLES)
    createAgentMock.mockResolvedValue(createMockCreateAgentResponse())
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('loading state', () => {
    it('shows loading message while fetching', () => {
      fetchAgentsMock.mockReturnValue(new Promise(() => {}))
      renderWithRouter(<AgentsPage />)
      expect(screen.getByText('Loading agents…')).toBeInTheDocument()
    })
  })

  describe('error state', () => {
    it('shows error message when fetchAgents rejects', async () => {
      fetchAgentsMock.mockRejectedValue(new Error('Network error'))
      renderWithRouter(<AgentsPage />)
      await waitFor(() => {
        expect(screen.getByText(/Error: Network error/)).toBeInTheDocument()
      })
    })

    it('shows generic error for non-Error rejections', async () => {
      fetchAgentsMock.mockRejectedValue('string error')
      renderWithRouter(<AgentsPage />)
      await waitFor(() => {
        expect(
          screen.getByText(/Error: Failed to load agents/),
        ).toBeInTheDocument()
      })
    })

    it('surfaces error message when fetchRoles rejects', async () => {
      fetchRolesMock.mockRejectedValue(new Error('Roles unavailable'))
      renderWithRouter(<AgentsPage />)
      await waitFor(() => {
        expect(
          screen.getByText(/Error: Roles unavailable/),
        ).toBeInTheDocument()
      })
    })

    it('surfaces generic error for non-Error roles rejections', async () => {
      fetchRolesMock.mockRejectedValue('roles boom')
      renderWithRouter(<AgentsPage />)
      await waitFor(() => {
        expect(
          screen.getByText(/Error: Failed to load roles/),
        ).toBeInTheDocument()
      })
    })
  })

  describe('empty state', () => {
    it('shows empty message when no agents exist', async () => {
      fetchAgentsMock.mockResolvedValue([])
      renderWithRouter(<AgentsPage />)
      await waitFor(() => {
        expect(
          screen.getByText(/No agents have been registered yet/),
        ).toBeInTheDocument()
      })
    })
  })

  describe('data rendering', () => {
    it('renders agent rows with label, roles, tool family, and created date', async () => {
      fetchAgentsMock.mockResolvedValue([
        createMockAgent({
          id: 1,
          agent_label: 'frontend-bot',
          tool_family: 'playwright',
          created_at: '2026-07-16T10:00:00Z',
          roles: [{ role_key: 'frontend', role_label: 'Frontend Engineer' }],
        }),
        createMockAgent({
          id: 2,
          agent_label: 'backend-bot',
          tool_family: 'codex',
          created_at: '2026-07-17T12:30:00Z',
          roles: [{ role_key: 'backend', role_label: 'Backend Engineer' }],
        }),
      ])
      renderWithRouter(<AgentsPage />)
      await waitFor(() => {
        expect(screen.getByText('frontend-bot')).toBeInTheDocument()
        expect(screen.getByText('backend-bot')).toBeInTheDocument()
        expect(screen.getByText('playwright')).toBeInTheDocument()
        expect(screen.getByText('codex')).toBeInTheDocument()
      })
    })

    it('shows em-dash for agents with no tool family', async () => {
      fetchAgentsMock.mockResolvedValue([
        createMockAgent({
          id: 1,
          agent_label: 'no-tools-agent',
          tool_family: null,
          roles: [{ role_key: 'frontend', role_label: 'Frontend Engineer' }],
        }),
      ])
      renderWithRouter(<AgentsPage />)
      await waitFor(() => {
        expect(screen.getByText('no-tools-agent')).toBeInTheDocument()
        // Two em-dashes: one for the null tool family, one for the roles
        // column is populated so only the tool-family cell renders a dash.
        expect(screen.getByText('—')).toBeInTheDocument()
      })
    })

    it('renders role badges for agents with roles', async () => {
      fetchAgentsMock.mockResolvedValue([
        createMockAgent({
          id: 1,
          agent_label: 'fullstack-agent',
          roles: [
            { role_key: 'frontend', role_label: 'Frontend Engineer' },
            { role_key: 'backend', role_label: 'Backend Engineer' },
          ],
        }),
      ])
      renderWithRouter(<AgentsPage />)
      await waitFor(() => {
        const badges = screen.getAllByText('Frontend Engineer')
        expect(badges).toHaveLength(1)
        expect(screen.getByText('Backend Engineer')).toBeInTheDocument()
      })
    })

    it('shows em-dash for agents with no roles', async () => {
      fetchAgentsMock.mockResolvedValue([
        createMockAgent({
          id: 1,
          agent_label: 'roleless-agent',
          roles: [],
        }),
      ])
      renderWithRouter(<AgentsPage />)
      await waitFor(() => {
        expect(screen.getByText('roleless-agent')).toBeInTheDocument()
        expect(screen.getByText('—')).toBeInTheDocument()
      })
    })

    it('shows the total count', async () => {
      fetchAgentsMock.mockResolvedValue([
        createMockAgent({ id: 1 }),
        createMockAgent({ id: 2 }),
        createMockAgent({ id: 3 }),
      ])
      renderWithRouter(<AgentsPage />)
      await waitFor(() => {
        expect(screen.getByText('3 total')).toBeInTheDocument()
      })
    })
  })

  describe('create agent flow', () => {
    it('shows + New Agent button', async () => {
      renderWithRouter(<AgentsPage />)
      await waitFor(() => {
        expect(screen.getByText('+ New Agent')).toBeInTheDocument()
      })
    })

    it('opens the create form drawer when + New Agent is clicked', async () => {
      renderWithRouter(<AgentsPage />)
      await waitFor(() => {
        expect(screen.getByText('+ New Agent')).toBeInTheDocument()
      })
      fireEvent.click(screen.getByText('+ New Agent'))
      expect(
        screen.getByRole('dialog', { name: 'New Agent' }),
      ).toBeInTheDocument()
      expect(screen.getByLabelText(/Agent Label/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/Tool Family/i)).toBeInTheDocument()
    })

    it('renders role checkboxes from fetched roles', async () => {
      renderWithRouter(<AgentsPage />)
      await waitFor(() => {
        expect(screen.getByText('+ New Agent')).toBeInTheDocument()
      })
      fireEvent.click(screen.getByText('+ New Agent'))
      expect(screen.getByText('Frontend Engineer')).toBeInTheDocument()
      expect(screen.getByText('Backend Engineer')).toBeInTheDocument()
    })

    it('shows hint when no roles are available', async () => {
      fetchRolesMock.mockResolvedValue([])
      renderWithRouter(<AgentsPage />)
      await waitFor(() => {
        expect(screen.getByText('+ New Agent')).toBeInTheDocument()
      })
      fireEvent.click(screen.getByText('+ New Agent'))
      expect(screen.getByText(/No roles available/i)).toBeInTheDocument()
    })

    it('validates that agent label is required', async () => {
      renderWithRouter(<AgentsPage />)
      await waitFor(() => {
        expect(screen.getByText('+ New Agent')).toBeInTheDocument()
      })
      fireEvent.click(screen.getByText('+ New Agent'))

      // Select a role but leave label empty.
      fireEvent.click(screen.getByText('Frontend Engineer'))
      fireEvent.click(screen.getByText('Create Agent'))

      expect(
        screen.getByText('Please provide an agent label.'),
      ).toBeInTheDocument()
      expect(createAgentMock).not.toHaveBeenCalled()
    })

    it('validates that at least one role is selected', async () => {
      renderWithRouter(<AgentsPage />)
      await waitFor(() => {
        expect(screen.getByText('+ New Agent')).toBeInTheDocument()
      })
      fireEvent.click(screen.getByText('+ New Agent'))

      fireEvent.change(screen.getByLabelText(/Agent Label/i), {
        target: { value: 'my-bot' },
      })
      fireEvent.click(screen.getByText('Create Agent'))

      expect(
        screen.getByText('Please select at least one role.'),
      ).toBeInTheDocument()
      expect(createAgentMock).not.toHaveBeenCalled()
    })

    it('calls createAgent with correct arguments on submit', async () => {
      renderWithRouter(<AgentsPage />)
      await waitFor(() => {
        expect(screen.getByText('+ New Agent')).toBeInTheDocument()
      })
      fireEvent.click(screen.getByText('+ New Agent'))

      fireEvent.change(screen.getByLabelText(/Agent Label/i), {
        target: { value: 'my-new-bot' },
      })
      fireEvent.change(screen.getByLabelText(/Tool Family/i), {
        target: { value: 'playwright' },
      })
      fireEvent.click(screen.getByText('Frontend Engineer'))
      fireEvent.click(screen.getByText('Create Agent'))

      await waitFor(() => {
        expect(createAgentMock).toHaveBeenCalledWith(
          'my-new-bot',
          'playwright',
          [1],
        )
      })
    })

    it('sends null for empty tool family', async () => {
      renderWithRouter(<AgentsPage />)
      await waitFor(() => {
        expect(screen.getByText('+ New Agent')).toBeInTheDocument()
      })
      fireEvent.click(screen.getByText('+ New Agent'))

      fireEvent.change(screen.getByLabelText(/Agent Label/i), {
        target: { value: 'my-bot' },
      })
      fireEvent.click(screen.getByText('Backend Engineer'))
      fireEvent.click(screen.getByText('Create Agent'))

      await waitFor(() => {
        expect(createAgentMock).toHaveBeenCalledWith('my-bot', null, [2])
      })
    })

    it('shows the token success view after successful creation', async () => {
      createAgentMock.mockResolvedValue(
        createMockCreateAgentResponse({
          agent_label: 'my-bot',
          api_token: 'ff_secret_token_xyz',
        }),
      )
      renderWithRouter(<AgentsPage />)
      await waitFor(() => {
        expect(screen.getByText('+ New Agent')).toBeInTheDocument()
      })
      fireEvent.click(screen.getByText('+ New Agent'))

      fireEvent.change(screen.getByLabelText(/Agent Label/i), {
        target: { value: 'my-bot' },
      })
      fireEvent.click(screen.getByText('Frontend Engineer'))
      fireEvent.click(screen.getByText('Create Agent'))

      await waitFor(() => {
        expect(
          screen.getByRole('dialog', { name: 'Agent Created' }),
        ).toBeInTheDocument()
      })
      expect(screen.getByDisplayValue('ff_secret_token_xyz')).toBeInTheDocument()
      expect(
        screen.getByText(/will not be shown again/i),
      ).toBeInTheDocument()
      expect(screen.getByText('Done')).toBeInTheDocument()
    })

    it('copies token to clipboard when Copy is clicked', async () => {
      const writeText = vi.fn().mockResolvedValue(undefined)
      Object.assign(navigator, {
        clipboard: { writeText },
      })

      createAgentMock.mockResolvedValue(
        createMockCreateAgentResponse({
          api_token: 'ff_copy_me',
        }),
      )
      renderWithRouter(<AgentsPage />)
      await waitFor(() => {
        expect(screen.getByText('+ New Agent')).toBeInTheDocument()
      })
      fireEvent.click(screen.getByText('+ New Agent'))

      fireEvent.change(screen.getByLabelText(/Agent Label/i), {
        target: { value: 'my-bot' },
      })
      fireEvent.click(screen.getByText('Frontend Engineer'))
      fireEvent.click(screen.getByText('Create Agent'))

      await waitFor(() => {
        expect(screen.getByDisplayValue('ff_copy_me')).toBeInTheDocument()
      })
      fireEvent.click(screen.getByText('Copy'))

      await waitFor(() => {
        expect(writeText).toHaveBeenCalledWith('ff_copy_me')
        expect(screen.getByText('✓ Copied')).toBeInTheDocument()
      })
    })

    it('shows error message when createAgent rejects', async () => {
      createAgentMock.mockRejectedValue(
        new Error('One or more selected roles no longer exist.'),
      )
      renderWithRouter(<AgentsPage />)
      await waitFor(() => {
        expect(screen.getByText('+ New Agent')).toBeInTheDocument()
      })
      fireEvent.click(screen.getByText('+ New Agent'))

      fireEvent.change(screen.getByLabelText(/Agent Label/i), {
        target: { value: 'my-bot' },
      })
      fireEvent.click(screen.getByText('Frontend Engineer'))
      fireEvent.click(screen.getByText('Create Agent'))

      await waitFor(() => {
        expect(
          screen.getByText('One or more selected roles no longer exist.'),
        ).toBeInTheDocument()
      })
      // Should still be on the form view, not the token view.
      expect(
        screen.queryByRole('dialog', { name: 'Agent Created' }),
      ).not.toBeInTheDocument()
    })

    it('refreshes agents list and closes drawer when Done is clicked', async () => {
      const createdAgent = createMockAgent({
        id: 99,
        agent_label: 'new-bot',
        roles: [{ role_key: 'frontend', role_label: 'Frontend Engineer' }],
      })
      createAgentMock.mockResolvedValue(
        createMockCreateAgentResponse({ agent_id: 99 }),
      )
      // First fetchAgents returns empty; after Done, the refresh returns the
      // new agent.
      fetchAgentsMock
        .mockResolvedValueOnce([])
        .mockResolvedValueOnce([createdAgent])

      renderWithRouter(<AgentsPage />)
      await waitFor(() => {
        expect(screen.getByText('+ New Agent')).toBeInTheDocument()
      })
      fireEvent.click(screen.getByText('+ New Agent'))

      fireEvent.change(screen.getByLabelText(/Agent Label/i), {
        target: { value: 'new-bot' },
      })
      fireEvent.click(screen.getByText('Frontend Engineer'))
      fireEvent.click(screen.getByText('Create Agent'))

      await waitFor(() => {
        expect(screen.getByText('Done')).toBeInTheDocument()
      })
      fireEvent.click(screen.getByText('Done'))

      await waitFor(() => {
        expect(fetchAgentsMock).toHaveBeenCalledTimes(2)
        expect(screen.getByText('new-bot')).toBeInTheDocument()
      })
      // Drawer should be closed.
      expect(
        screen.queryByRole('dialog', { name: 'Agent Created' }),
      ).not.toBeInTheDocument()
    })

    it('shows fallback guidance and selects token when clipboard fails', async () => {
      const writeText = vi.fn().mockRejectedValue(new Error('not allowed'))
      Object.assign(navigator, {
        clipboard: { writeText },
      })

      createAgentMock.mockResolvedValue(
        createMockCreateAgentResponse({
          api_token: 'ff_fail_copy',
        }),
      )
      renderWithRouter(<AgentsPage />)
      await waitFor(() => {
        expect(screen.getByText('+ New Agent')).toBeInTheDocument()
      })
      fireEvent.click(screen.getByText('+ New Agent'))

      fireEvent.change(screen.getByLabelText(/Agent Label/i), {
        target: { value: 'my-bot' },
      })
      fireEvent.click(screen.getByText('Frontend Engineer'))
      fireEvent.click(screen.getByText('Create Agent'))

      await waitFor(() => {
        expect(screen.getByDisplayValue('ff_fail_copy')).toBeInTheDocument()
      })
      fireEvent.click(screen.getByText('Copy'))

      await waitFor(() => {
        expect(writeText).toHaveBeenCalledWith('ff_fail_copy')
        expect(
          screen.getByText(/Automatic copy failed/i),
        ).toBeInTheDocument()
      })
      // Should NOT show the "✓ Copied" success state.
      expect(screen.queryByText('✓ Copied')).not.toBeInTheDocument()
    })
  })
})
