import { describe, expect, it, vi, beforeEach } from 'vitest'
import { useStore, resetStore } from './index'
import { createMockRole } from '../test/utils'

// Hoist the mock service before the hoisted vi.mock factory runs.
const { mockService } = vi.hoisted(() => ({
  mockService: {
    getProfile: vi.fn(),
    createProfile: vi.fn(),
    fetchRoles: vi.fn(),
    fetchAgents: vi.fn(),
  },
}))

vi.mock('@job-service', () => ({ jobService: mockService }))

const getProfileMock = vi.mocked(mockService.getProfile)

describe('profileSlice', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    resetStore()
  })

  it('starts unchecked, not loading, no error', () => {
    const { profile } = useStore.getState()
    expect(profile.isOnboarded).toBeNull()
    expect(profile.isLoading).toBe(false)
    expect(profile.error).toBeNull()
  })

  it('check() resolves isOnboarded from the server', async () => {
    getProfileMock.mockResolvedValue(true)
    await useStore.getState().profile.check()
    expect(getProfileMock).toHaveBeenCalledTimes(1)
    expect(useStore.getState().profile.isOnboarded).toBe(true)
    expect(useStore.getState().profile.isLoading).toBe(false)
    expect(useStore.getState().profile.error).toBeNull()
  })

  it('check() surfaces Error.message on rejection', async () => {
    getProfileMock.mockRejectedValue(new Error('Server error'))
    await useStore.getState().profile.check()
    expect(useStore.getState().profile.isOnboarded).toBeNull()
    expect(useStore.getState().profile.error).toBe('Server error')
    expect(useStore.getState().profile.isLoading).toBe(false)
  })

  it('check() surfaces a generic message for non-Error rejections', async () => {
    getProfileMock.mockRejectedValue('boom')
    await useStore.getState().profile.check()
    expect(useStore.getState().profile.error).toBe(
      'Failed to check onboarding status',
    )
  })

  it('setOnboarded() writes the value locally and clears error', async () => {
    getProfileMock.mockRejectedValue(new Error('x'))
    await useStore.getState().profile.check()
    expect(useStore.getState().profile.error).toBe('x')

    useStore.getState().profile.setOnboarded(true)
    expect(useStore.getState().profile.isOnboarded).toBe(true)
    expect(useStore.getState().profile.error).toBeNull()
  })
})

describe('rolesSlice', () => {
  const fetchRolesMock = vi.mocked(mockService.fetchRoles)

  beforeEach(() => {
    vi.clearAllMocks()
    resetStore()
  })

  it('fetch() stores items and stamps fetchedAt', async () => {
    const roles = [createMockRole({ id: 1, role_key: 'a' })]
    fetchRolesMock.mockResolvedValue(roles)
    await useStore.getState().roles.fetch()
    expect(useStore.getState().roles.items).toBe(roles)
    expect(useStore.getState().roles.fetchedAt).toBeTypeOf('number')
    expect(useStore.getState().roles.isLoading).toBe(false)
    expect(useStore.getState().roles.error).toBeNull()
  })

  it('fetch() skips the network when the cache is fresh', async () => {
    fetchRolesMock.mockResolvedValue([createMockRole()])
    await useStore.getState().roles.fetch()
    expect(fetchRolesMock).toHaveBeenCalledTimes(1)

    // Second call within the TTL window must NOT hit the service again.
    await useStore.getState().roles.fetch()
    expect(fetchRolesMock).toHaveBeenCalledTimes(1)
  })

  it('fetch(force=true) bypasses the cache', async () => {
    fetchRolesMock.mockResolvedValue([createMockRole({ id: 1 })])
    await useStore.getState().roles.fetch()
    await useStore.getState().roles.fetch(true)
    expect(fetchRolesMock).toHaveBeenCalledTimes(2)
  })

  it('invalidate() forces the next fetch to hit the network', async () => {
    fetchRolesMock.mockResolvedValue([createMockRole()])
    await useStore.getState().roles.fetch()
    expect(fetchRolesMock).toHaveBeenCalledTimes(1)
    useStore.getState().roles.invalidate()
    // invalidate alone does not refetch; it just clears the cache.
    expect(useStore.getState().roles.fetchedAt).toBeNull()
    await useStore.getState().roles.fetch()
    expect(fetchRolesMock).toHaveBeenCalledTimes(2)
  })

  it('fetch() surfaces Error.message on rejection', async () => {
    fetchRolesMock.mockRejectedValue(new Error('Network error'))
    await useStore.getState().roles.fetch()
    expect(useStore.getState().roles.error).toBe('Network error')
    expect(useStore.getState().roles.isLoading).toBe(false)
  })

  it('fetch() surfaces a generic message for non-Error rejections', async () => {
    fetchRolesMock.mockRejectedValue('boom')
    await useStore.getState().roles.fetch()
    expect(useStore.getState().roles.error).toBe('Failed to load roles')
  })

  it('concurrent fetch() calls coalesce into one network request', async () => {
    fetchRolesMock.mockResolvedValue([createMockRole()])
    await Promise.all([
      useStore.getState().roles.fetch(),
      useStore.getState().roles.fetch(),
      useStore.getState().roles.fetch(),
    ])
    expect(fetchRolesMock).toHaveBeenCalledTimes(1)
  })
})

describe('agentsSlice', () => {
  const fetchAgentsMock = vi.mocked(mockService.fetchAgents)

  beforeEach(() => {
    vi.clearAllMocks()
    resetStore()
  })

  it('fetch() stores items and stamps fetchedAt', async () => {
    fetchAgentsMock.mockResolvedValue([])
    await useStore.getState().agents.fetch()
    expect(useStore.getState().agents.items).toEqual([])
    expect(useStore.getState().agents.fetchedAt).toBeTypeOf('number')
    expect(useStore.getState().agents.isLoading).toBe(false)
  })

  it('fetch() skips the network when fresh', async () => {
    fetchAgentsMock.mockResolvedValue([])
    await useStore.getState().agents.fetch()
    await useStore.getState().agents.fetch()
    expect(fetchAgentsMock).toHaveBeenCalledTimes(1)
  })

  it('fetch(true) bypasses the cache', async () => {
    fetchAgentsMock.mockResolvedValue([])
    await useStore.getState().agents.fetch()
    await useStore.getState().agents.fetch(true)
    expect(fetchAgentsMock).toHaveBeenCalledTimes(2)
  })

  it('invalidate() clears the cache', async () => {
    fetchAgentsMock.mockResolvedValue([])
    await useStore.getState().agents.fetch()
    useStore.getState().agents.invalidate()
    expect(useStore.getState().agents.fetchedAt).toBeNull()
  })

  it('fetch() surfaces Error.message on rejection', async () => {
    fetchAgentsMock.mockRejectedValue(new Error('boom'))
    await useStore.getState().agents.fetch()
    expect(useStore.getState().agents.error).toBe('boom')
  })

  it('addLocal() appends an agent without a refetch', async () => {
    fetchAgentsMock.mockResolvedValue([])
    await useStore.getState().agents.fetch()
    const before = useStore.getState().agents.items.length
    useStore.getState().agents.addLocal({
      id: 7,
      agent_label: 'new-bot',
      tool_family: null,
      created_at: '2026-01-01T00:00:00Z',
      roles: [],
    })
    expect(useStore.getState().agents.items).toHaveLength(before + 1)
    expect(useStore.getState().agents.items.at(-1)?.agent_label).toBe('new-bot')
    // addLocal is optimistic — it must NOT hit the service.
    expect(fetchAgentsMock).toHaveBeenCalledTimes(1)
  })

  it('resetStore() clears all slices back to initial state', async () => {
    const fetchRolesMockLocal = vi.mocked(mockService.fetchRoles)
    fetchAgentsMock.mockResolvedValue([])
    fetchRolesMockLocal.mockResolvedValue([createMockRole()])
    getProfileMock.mockResolvedValue(true)
    await useStore.getState().agents.fetch()
    await useStore.getState().roles.fetch()
    await useStore.getState().profile.check()
    expect(useStore.getState().agents.fetchedAt).not.toBeNull()

    resetStore()
    expect(useStore.getState().agents.items).toEqual([])
    expect(useStore.getState().agents.fetchedAt).toBeNull()
    expect(useStore.getState().roles.items).toEqual([])
    expect(useStore.getState().profile.isOnboarded).toBeNull()
  })
})
