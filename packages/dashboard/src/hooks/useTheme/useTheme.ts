import { useCallback, useEffect, useState } from 'react'

export type Theme = 'light' | 'dark'

const STORAGE_KEY = 'ff-theme'
const DARK_MEDIA = '(prefers-color-scheme: dark)'

function readInitialTheme(): Theme {
  // The inline script in index.html sets data-theme before paint.
  // We read from the DOM so React state matches what's already rendered.
  if (typeof document !== 'undefined' && document.documentElement.dataset.theme === 'dark') {
    return 'dark'
  }
  return 'light'
}

function applyTheme(theme: Theme) {
  if (theme === 'dark') {
    document.documentElement.dataset.theme = 'dark'
  } else {
    // Light is the default (:root); remove the override.
    delete document.documentElement.dataset.theme
  }
}

/**
 * Theme controller for the dashboard.
 *
 * - Initial state is read from the DOM (set by the FOUC-prevention script
 *   in index.html), so React and the rendered page never disagree.
 * - `toggleTheme` flips the theme, persists it to localStorage, and updates
 *   the DOM. Once the user toggles, a manual override is stored and system
 *   preference changes are ignored.
 * - When no manual override is stored, the hook listens to
 *   `prefers-color-scheme` changes and follows the OS live.
 */
export function useTheme() {
  const [theme, setTheme] = useState<Theme>(readInitialTheme)

  const persist = useCallback((next: Theme) => {
    try {
      localStorage.setItem(STORAGE_KEY, next)
    } catch (_) {
      /* storage may be unavailable; DOM update still applies */
    }
  }, [])

  const toggleTheme = useCallback(() => {
    setTheme((prev) => {
      const next: Theme = prev === 'dark' ? 'light' : 'dark'
      applyTheme(next)
      persist(next)
      return next
    })
  }, [persist])

  // Follow system preference when the user hasn't set a manual override.
  useEffect(() => {
    let stored: string | null = null
    try {
      stored = localStorage.getItem(STORAGE_KEY)
    } catch (_) {
      stored = null
    }
    if (stored === 'light' || stored === 'dark') {
      // Manual override exists; don't react to system changes.
      return
    }

    const mql = window.matchMedia(DARK_MEDIA)
    const onChange = (e: MediaQueryListEvent) => {
      const next: Theme = e.matches ? 'dark' : 'light'
      applyTheme(next)
      setTheme(next)
    }
    mql.addEventListener('change', onChange)
    return () => mql.removeEventListener('change', onChange)
  }, [])

  return { theme, toggleTheme }
}
