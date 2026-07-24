import { describe, expect, it, vi } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import { ThemeToggle } from './ThemeToggle'
import { renderWithRouter } from '../../test/utils'

// Mock useTheme so we can control the theme value and spy on toggleTheme.
vi.mock('../../hooks/useTheme/useTheme', () => ({
  useTheme: vi.fn(() => ({
    theme: 'light',
    toggleTheme: vi.fn(),
  })),
}))

import { useTheme } from '../../hooks/useTheme/useTheme'

describe('ThemeToggle', () => {
  it('renders a button with light-theme aria-label when theme is light', () => {
    vi.mocked(useTheme).mockReturnValue({
      theme: 'light',
      toggleTheme: vi.fn(),
    })
    renderWithRouter(<ThemeToggle />)
    expect(
      screen.getByRole('button', { name: 'Switch to dark theme' }),
    ).toBeInTheDocument()
  })

  it('renders a button with dark-theme aria-label when theme is dark', () => {
    vi.mocked(useTheme).mockReturnValue({
      theme: 'dark',
      toggleTheme: vi.fn(),
    })
    renderWithRouter(<ThemeToggle />)
    expect(
      screen.getByRole('button', { name: 'Switch to light theme' }),
    ).toBeInTheDocument()
  })

  it('calls toggleTheme when clicked', () => {
    const toggleTheme = vi.fn()
    vi.mocked(useTheme).mockReturnValue({
      theme: 'light',
      toggleTheme,
    })
    renderWithRouter(<ThemeToggle />)
    fireEvent.click(screen.getByRole('button'))
    expect(toggleTheme).toHaveBeenCalledTimes(1)
  })
})
