import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useTheme } from './useTheme'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const STORAGE_KEY = 'ff-theme'
const DARK_MEDIA = '(prefers-color-scheme: dark)'

function setDomTheme(theme: 'dark' | 'light') {
  if (theme === 'dark') {
    document.documentElement.dataset.theme = 'dark'
  } else {
    delete document.documentElement.dataset.theme
  }
}

function clearStorage() {
  localStorage.clear()
}

/**
 * Create a mock matchMedia that supports dispatching change events.
 */
function mockMatchMedia(matches: boolean) {
  const listeners: ((e: MediaQueryListEvent) => void)[] = []
  const mql: MediaQueryList = {
    matches,
    media: DARK_MEDIA,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: (_type: string, listener: EventListenerOrEventListenerObject) => {
      if (typeof listener === 'function') listeners.push(listener)
    },
    removeEventListener: (_type: string, listener: EventListenerOrEventListenerObject) => {
      if (typeof listener === 'function') {
        const idx = listeners.indexOf(listener)
        if (idx >= 0) listeners.splice(idx, 1)
      }
    },
    dispatchEvent: () => false,
  }
  return {
    mql,
    // Simulate a system preference change.
    fireChange: (newMatches: boolean) => {
      const event = { matches: newMatches } as MediaQueryListEvent
      for (const listener of listeners) listener(event)
    },
  }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useTheme', () => {
  beforeEach(() => {
    clearStorage()
    setDomTheme('light')
  })

  afterEach(() => {
    clearStorage()
    setDomTheme('light')
    vi.restoreAllMocks()
  })

  describe('readInitialTheme', () => {
    it('returns "dark" when DOM data-theme is "dark"', () => {
      setDomTheme('dark')
      const { result } = renderHook(() => useTheme())
      expect(result.current.theme).toBe('dark')
    })

    it('returns "light" when DOM data-theme is not set', () => {
      setDomTheme('light')
      const { result } = renderHook(() => useTheme())
      expect(result.current.theme).toBe('light')
    })
  })

  describe('toggleTheme', () => {
    it('flips from light to dark', () => {
      setDomTheme('light')
      const { result } = renderHook(() => useTheme())

      act(() => result.current.toggleTheme())

      expect(result.current.theme).toBe('dark')
    })

    it('flips from dark to light', () => {
      setDomTheme('dark')
      const { result } = renderHook(() => useTheme())

      act(() => result.current.toggleTheme())

      expect(result.current.theme).toBe('light')
    })

    it('persists to localStorage', () => {
      setDomTheme('light')
      const { result } = renderHook(() => useTheme())

      act(() => result.current.toggleTheme())

      expect(localStorage.getItem(STORAGE_KEY)).toBe('dark')
    })

    it('updates the DOM data-theme attribute', () => {
      setDomTheme('light')
      const { result } = renderHook(() => useTheme())

      act(() => result.current.toggleTheme())

      expect(document.documentElement.dataset.theme).toBe('dark')
    })

    it('removes DOM data-theme when switching to light', () => {
      setDomTheme('dark')
      const { result } = renderHook(() => useTheme())

      act(() => result.current.toggleTheme())

      expect(document.documentElement.dataset.theme).toBeUndefined()
    })
  })

  describe('system preference following', () => {
    it('listens to matchMedia changes when no manual override is stored', () => {
      const { mql, fireChange } = mockMatchMedia(false)
      vi.spyOn(window, 'matchMedia').mockReturnValue(mql)

      setDomTheme('light')
      const { result } = renderHook(() => useTheme())

      expect(result.current.theme).toBe('light')

      act(() => fireChange(true))

      expect(result.current.theme).toBe('dark')
      expect(document.documentElement.dataset.theme).toBe('dark')
    })

    it('does not attach matchMedia listener when a manual override is stored', () => {
      localStorage.setItem(STORAGE_KEY, 'light')
      const matchMediaSpy = vi.spyOn(window, 'matchMedia')

      setDomTheme('light')
      renderHook(() => useTheme())

      // matchMedia should not be called because a manual override exists
      expect(matchMediaSpy).not.toHaveBeenCalled()
    })
  })

  describe('storage unavailable', () => {
    it('does not crash when localStorage.setItem throws', () => {
      setDomTheme('light')
      vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
        throw new Error('Storage unavailable')
      })

      const { result } = renderHook(() => useTheme())

      // Should not throw
      act(() => result.current.toggleTheme())

      // DOM should still be updated
      expect(document.documentElement.dataset.theme).toBe('dark')
    })
  })
})
