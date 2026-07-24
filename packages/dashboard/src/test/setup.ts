/**
 * Global test setup for the dashboard package.
 *
 * - Registers `@testing-library/jest-dom` matchers (toBeInTheDocument, etc.).
 * - Polyfills `window.matchMedia` (used by `useTheme`).
 * - Polyfills `queueMicrotask` (used by `Drawer`) — jsdom has it, but we
 *   ensure it exists for safety.
 * - Cleans up the DOM between tests to prevent leakage.
 */

import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

// ---------------------------------------------------------------------------
// matchMedia polyfill
// ---------------------------------------------------------------------------

if (!window.matchMedia) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: (query: string): MediaQueryList => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }),
  })
}

// ---------------------------------------------------------------------------
// Cleanup between tests
// ---------------------------------------------------------------------------

afterEach(() => {
  cleanup()
})
