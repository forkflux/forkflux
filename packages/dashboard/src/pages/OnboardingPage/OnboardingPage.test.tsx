import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import { OnboardingPage } from './OnboardingPage'
import {
  renderWithRouter,
  createMockRole,
  createMockAgent,
  createMockCreateAgentResponse,
} from '../../test/utils'
import '@testing-library/jest-dom/vitest'

// Use vi.hoisted so the mock service is created before the hoisted vi.mock
// factory runs.
const { mockService } = vi.hoisted(() => {
  const service = {
    fetchRoles: vi.fn(),
    fetchAgents: vi.fn(),
    createRole: vi.fn(),
    createAgent: vi.fn(),
    createProfile: vi.fn(),
  }
  return { mockService: service }
})

vi.mock('@job-service', () => ({
  jobService: mockService,
}))

const fetchRolesMock = vi.mocked(mockService.fetchRoles)
const fetchAgentsMock = vi.mocked(mockService.fetchAgents)
const createRoleMock = vi.mocked(mockService.createRole)
const createAgentMock = vi.mocked(mockService.createAgent)
const createProfileMock = vi.mocked(mockService.createProfile)

const MOCK_ROLES = [
  createMockRole({ id: 1, role_key: 'frontend', role_label: 'Frontend Engineer' }),
  createMockRole({ id: 2, role_key: 'backend', role_label: 'Backend Engineer' }),
]

const MOCK_AGENTS = [
  createMockAgent({
    id: 1,
    agent_label: 'frontend-bot',
    tool_family: 'playwright',
    roles: [{ role_key: 'frontend', role_label: 'Frontend Engineer' }],
  }),
]

describe('OnboardingPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    fetchRolesMock.mockResolvedValue([])
    fetchAgentsMock.mockResolvedValue([])
    createRoleMock.mockResolvedValue(createMockRole())
    createAgentMock.mockResolvedValue(createMockCreateAgentResponse())
    createProfileMock.mockResolvedValue(true)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  // ── loading / error ────────────────────────────────────────────

  describe('loading state', () => {
    it('shows loading message while fetching', () => {
      fetchRolesMock.mockReturnValue(new Promise(() => {}))
      renderWithRouter(<OnboardingPage />)
      expect(screen.getByText('Loading…')).toBeInTheDocument()
    })
  })

  describe('error state', () => {
    it('shows error message when fetchRoles rejects', async () => {
      fetchRolesMock.mockRejectedValue(new Error('Network error'))
      renderWithRouter(<OnboardingPage />)
      await waitFor(() => {
        expect(screen.getByText(/Error: Network error/)).toBeInTheDocument()
      })
    })

    it('shows generic error for non-Error rejections', async () => {
      fetchRolesMock.mockRejectedValue('string error')
      renderWithRouter(<OnboardingPage />)
      await waitFor(() => {
        expect(
          screen.getByText(/Error: Failed to load data/),
        ).toBeInTheDocument()
      })
    })
  })

  // ── step 1: roles ──────────────────────────────────────────────

  describe('step 1 — roles', () => {
    it('renders step 1 by default', async () => {
      renderWithRouter(<OnboardingPage />)
      await waitFor(() => {
        expect(
          screen.getByText('Step 1: Add workflow roles'),
        ).toBeInTheDocument()
      })
    })

    it('shows existing roles in a table', async () => {
      fetchRolesMock.mockResolvedValue(MOCK_ROLES)
      renderWithRouter(<OnboardingPage />)
      await waitFor(() => {
        expect(screen.getByText('Frontend Engineer')).toBeInTheDocument()
        expect(screen.getByText('Backend Engineer')).toBeInTheDocument()
      })
    })

    it('Continue button is disabled when no roles exist', async () => {
      fetchRolesMock.mockResolvedValue([])
      renderWithRouter(<OnboardingPage />)
      await waitFor(() => {
        expect(
          screen.getByText('Step 1: Add workflow roles'),
        ).toBeInTheDocument()
      })
      expect(screen.getByText('Continue')).toBeDisabled()
    })

    it('Continue button is enabled when at least one role exists', async () => {
      fetchRolesMock.mockResolvedValue(MOCK_ROLES)
      renderWithRouter(<OnboardingPage />)
      await waitFor(() => {
        expect(screen.getByText('Continue')).not.toBeDisabled()
      })
    })

    it('can add a role and see it in the list', async () => {
      fetchRolesMock.mockResolvedValue([])
      createRoleMock.mockResolvedValue(
        createMockRole({ id: 10, role_key: 'qa', role_label: 'QA Engineer' }),
      )
      // After creation, refresh returns the new role.
      fetchRolesMock
        .mockResolvedValueOnce([]) // initial load
        .mockResolvedValueOnce([
          createMockRole({ id: 10, role_key: 'qa', role_label: 'QA Engineer' }),
        ]) // after refresh

      renderWithRouter(<OnboardingPage />)
      await waitFor(() => {
        expect(screen.getByText('Continue')).toBeInTheDocument()
      })

      fireEvent.change(screen.getByPlaceholderText('e.g. Frontend Engineer'), {
        target: { value: 'QA Engineer' },
      })
      fireEvent.click(screen.getByText('Add Role'))

      await waitFor(() => {
        expect(createRoleMock).toHaveBeenCalledWith('qa_engineer', 'QA Engineer')
      })
      await waitFor(() => {
        expect(screen.getByText('QA Engineer')).toBeInTheDocument()
      })
    })

    it('shows validation error when role label is empty', async () => {
      renderWithRouter(<OnboardingPage />)
      await waitFor(() => {
        expect(screen.getByText('Add Role')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('Add Role'))
      await waitFor(() => {
        expect(
          screen.getByText('Please provide a role label.'),
        ).toBeInTheDocument()
      })
    })

    it('navigates to step 2 when Continue is clicked', async () => {
      fetchRolesMock.mockResolvedValue(MOCK_ROLES)
      renderWithRouter(<OnboardingPage />)
      await waitFor(() => {
        expect(screen.getByText('Continue')).not.toBeDisabled()
      })

      fireEvent.click(screen.getByText('Continue'))
      await waitFor(() => {
        expect(
          screen.getByText('Step 2: Add agents'),
        ).toBeInTheDocument()
      })
    })
  })

  // ── step 2: agents ─────────────────────────────────────────────

  describe('step 2 — agents', () => {
    async function goToStep2() {
      fetchRolesMock.mockResolvedValue(MOCK_ROLES)
      renderWithRouter(<OnboardingPage />)
      await waitFor(() => {
        expect(screen.getByText('Continue')).not.toBeDisabled()
      })
      fireEvent.click(screen.getByText('Continue'))
      await waitFor(() => {
        expect(screen.getByText('Step 2: Add agents')).toBeInTheDocument()
      })
    }

    it('shows existing agents in a table', async () => {
      fetchAgentsMock.mockResolvedValue(MOCK_AGENTS)
      await goToStep2()
      await waitFor(() => {
        expect(screen.getByText('frontend-bot')).toBeInTheDocument()
      })
    })

    it('Continue button is disabled when no agents exist', async () => {
      fetchAgentsMock.mockResolvedValue([])
      await goToStep2()
      await waitFor(() => {
        expect(screen.getByText('Continue')).toBeDisabled()
      })
    })

    it('Continue button is enabled when at least one agent exists', async () => {
      fetchAgentsMock.mockResolvedValue(MOCK_AGENTS)
      await goToStep2()
      await waitFor(() => {
        expect(screen.getByText('Continue')).not.toBeDisabled()
      })
    })

    it('can create an agent and see the token success view', async () => {
      // First fetch (during goToStep2) returns empty; second fetch
      // (refreshAgents after creation) returns agents so Continue enables.
      fetchAgentsMock
        .mockResolvedValueOnce([])
        .mockResolvedValue(MOCK_AGENTS)
      await goToStep2()

      fireEvent.change(screen.getByPlaceholderText('e.g. frontend-bot'), {
        target: { value: 'my-bot' },
      })
      // Select the first role checkbox
      const checkboxes = screen.getAllByRole('checkbox')
      fireEvent.click(checkboxes[0])

      fireEvent.click(screen.getByText('Create Agent'))

      await waitFor(() => {
        expect(createAgentMock).toHaveBeenCalledWith('my-bot', null, [1])
      })
      // The mock returns the default agent_label 'frontend-bot'
      await waitFor(() => {
        expect(
          screen.getByText(/Agent Created: frontend-bot/),
        ).toBeInTheDocument()
      })
      // Token warning should be visible
      expect(
        screen.getByText(/Copy your API token now/),
      ).toBeInTheDocument()
      // MCP config should be visible
      expect(
        screen.getByText('MCP Server Configuration'),
      ).toBeInTheDocument()

      // After refreshAgents, canProceedFromStep2 (agents.length >= 1)
      // becomes true and Continue is enabled.
      await waitFor(() => {
        expect(screen.getByText('Continue')).not.toBeDisabled()
      })
    })

    it('shows validation error when agent label is empty', async () => {
      await goToStep2()

      fireEvent.click(screen.getByText('Create Agent'))
      await waitFor(() => {
        expect(
          screen.getByText('Please provide an agent label.'),
        ).toBeInTheDocument()
      })
    })

    it('shows validation error when no roles are selected', async () => {
      await goToStep2()

      fireEvent.change(screen.getByPlaceholderText('e.g. frontend-bot'), {
        target: { value: 'my-bot' },
      })
      fireEvent.click(screen.getByText('Create Agent'))
      await waitFor(() => {
        expect(
          screen.getByText('Please select at least one role.'),
        ).toBeInTheDocument()
      })
    })

    it('can add another agent after the first', async () => {
      fetchAgentsMock.mockResolvedValue([])
      await goToStep2()

      // Create first agent
      fireEvent.change(screen.getByPlaceholderText('e.g. frontend-bot'), {
        target: { value: 'bot-1' },
      })
      const checkboxes = screen.getAllByRole('checkbox')
      fireEvent.click(checkboxes[0])
      fireEvent.click(screen.getByText('Create Agent'))

      // The mock returns the default agent_label 'frontend-bot'
      await waitFor(() => {
        expect(screen.getByText(/Agent Created: frontend-bot/)).toBeInTheDocument()
      })

      // Click "Add Another Agent"
      fireEvent.click(screen.getByText('+ Add Another Agent'))

      await waitFor(() => {
        // Should be back to the create form
        expect(screen.getByText('Create Agent')).toBeInTheDocument()
      })
    })

    it('Back button returns to step 1', async () => {
      await goToStep2()

      fireEvent.click(screen.getByText('← Back'))
      await waitFor(() => {
        expect(
          screen.getByText('Step 1: Add workflow roles'),
        ).toBeInTheDocument()
      })
    })

    it('navigates to step 3 when Continue is clicked', async () => {
      fetchAgentsMock.mockResolvedValue(MOCK_AGENTS)
      await goToStep2()
      await waitFor(() => {
        expect(screen.getByText('Continue')).not.toBeDisabled()
      })

      fireEvent.click(screen.getByText('Continue'))
      await waitFor(() => {
        expect(
          screen.getByText('Step 3: Complete setup'),
        ).toBeInTheDocument()
      })
    })
  })

  // ── step 3: complete ───────────────────────────────────────────

  describe('step 3 — complete', () => {
    async function goToStep3() {
      fetchRolesMock.mockResolvedValue(MOCK_ROLES)
      fetchAgentsMock.mockResolvedValue(MOCK_AGENTS)
      renderWithRouter(<OnboardingPage />)
      // Step 1 → Step 2
      await waitFor(() => {
        expect(screen.getByText('Continue')).not.toBeDisabled()
      })
      fireEvent.click(screen.getByText('Continue'))
      // Step 2 → Step 3
      await waitFor(() => {
        expect(screen.getByText('Continue')).not.toBeDisabled()
      })
      fireEvent.click(screen.getByText('Continue'))
      await waitFor(() => {
        expect(
          screen.getByText('Step 3: Complete setup'),
        ).toBeInTheDocument()
      })
    }

    it('shows summary with role and agent counts', async () => {
      await goToStep3()
      expect(screen.getByText(/2 roles/)).toBeInTheDocument()
      expect(screen.getByText(/1 agent/)).toBeInTheDocument()
    })

    it('calls createProfile and navigates on Finish Setup', async () => {
      await goToStep3()

      fireEvent.click(screen.getByText('Finish Setup'))
      await waitFor(() => {
        expect(createProfileMock).toHaveBeenCalledWith(true)
      })
    })

    it('shows error when createProfile fails', async () => {
      createProfileMock.mockRejectedValue(new Error('Server error'))
      await goToStep3()

      fireEvent.click(screen.getByText('Finish Setup'))
      await waitFor(() => {
        expect(screen.getByText(/Server error/)).toBeInTheDocument()
      })
    })

    it('Back button returns to step 2', async () => {
      await goToStep3()

      fireEvent.click(screen.getByText('← Back'))
      await waitFor(() => {
        expect(
          screen.getByText('Step 2: Add agents'),
        ).toBeInTheDocument()
      })
    })
  })
})