import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { useState } from 'react'
import { Drawer } from './Drawer'
import { renderWithRouter } from '../../test/utils'

describe('Drawer', () => {
  describe('rendering', () => {
    it('renders nothing when open is false', () => {
      renderWithRouter(
        <Drawer open={false} onClose={vi.fn()}>
          <p>Drawer content</p>
        </Drawer>,
      )
      expect(screen.queryByText('Drawer content')).not.toBeInTheDocument()
    })

    it('renders panel and overlay when open is true', () => {
      renderWithRouter(
        <Drawer open={true} onClose={vi.fn()}>
          <p>Drawer content</p>
        </Drawer>,
      )
      expect(screen.getByText('Drawer content')).toBeInTheDocument()
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    it('renders title in the header when provided', () => {
      renderWithRouter(
        <Drawer open={true} onClose={vi.fn()} title="Context Payload">
          <p>Content</p>
        </Drawer>,
      )
      expect(screen.getByText('Context Payload')).toBeInTheDocument()
    })

    it('does not render header when title is not provided', () => {
      renderWithRouter(
        <Drawer open={true} onClose={vi.fn()}>
          <p>Content</p>
        </Drawer>,
      )
      expect(screen.queryByRole('heading')).not.toBeInTheDocument()
    })

    it('applies custom width to the panel', () => {
      renderWithRouter(
        <Drawer open={true} onClose={vi.fn()} width="90%">
          <p>Content</p>
        </Drawer>,
      )
      const panel = screen.getByRole('dialog')
      expect(panel).toHaveStyle({ width: '90%' })
    })
  })

  describe('close interactions', () => {
    it('calls onClose when ESC key is pressed', () => {
      const onClose = vi.fn()
      renderWithRouter(
        <Drawer open={true} onClose={onClose}>
          <p>Content</p>
        </Drawer>,
      )
      fireEvent.keyDown(document, { key: 'Escape' })
      expect(onClose).toHaveBeenCalledTimes(1)
    })

    it('calls onClose when the backdrop is clicked', () => {
      const onClose = vi.fn()
      renderWithRouter(
        <Drawer open={true} onClose={onClose}>
          <p>Content</p>
        </Drawer>,
      )
      const overlay = screen.getByRole('dialog').previousElementSibling
      expect(overlay).not.toBeNull()
      fireEvent.click(overlay!)
      expect(onClose).toHaveBeenCalledTimes(1)
    })

    it('calls onClose when the close button is clicked', () => {
      const onClose = vi.fn()
      renderWithRouter(
        <Drawer open={true} onClose={onClose} title="Test">
          <p>Content</p>
        </Drawer>,
      )
      fireEvent.click(screen.getByLabelText('Close'))
      expect(onClose).toHaveBeenCalledTimes(1)
    })
  })

  describe('body scroll lock', () => {
    it('sets body overflow to hidden when open', () => {
      renderWithRouter(
        <Drawer open={true} onClose={vi.fn()}>
          <p>Content</p>
        </Drawer>,
      )
      expect(document.body.style.overflow).toBe('hidden')
    })

    it('restores body overflow when closed (unmounted)', () => {
      document.body.style.overflow = 'visible'
      const { unmount } = renderWithRouter(
        <Drawer open={true} onClose={vi.fn()}>
          <p>Content</p>
        </Drawer>,
      )
      expect(document.body.style.overflow).toBe('hidden')
      unmount()
      expect(document.body.style.overflow).toBe('visible')
    })
  })

  describe('focus management', () => {
    it('moves focus into the panel when opened', async () => {
      renderWithRouter(
        <Drawer open={true} onClose={vi.fn()} title="Test">
          <p>Content</p>
        </Drawer>,
      )
      const panel = screen.getByRole('dialog')
      // Focus is moved via queueMicrotask; flush it with a microtask await
      await Promise.resolve()
      expect(document.activeElement).toBe(panel)
    })

    /**
     * Regression: when a parent re-renders with a fresh inline `onClose`
     * arrow function (e.g. on every keystroke in a form field), the drawer's
     * focus-management effect must NOT re-run and steal focus from the input
     * the user is actively typing in.
     */
    it('does not steal focus from an input when the parent re-renders with a new onClose', async () => {
      function Parent() {
        const [value, setValue] = useState('')
        return (
          <Drawer open={true} onClose={() => {}} title="Test">
            <input
              data-testid="field"
              value={value}
              onChange={(e) => setValue(e.target.value)}
            />
          </Drawer>
        )
      }

      render(<Parent />)
      const input = screen.getByTestId('field') as HTMLInputElement

      // Flush the initial open-focus microtask (focus moves to the panel on
      // open), then simulate the user clicking into the input field.
      await Promise.resolve()
      input.focus()
      expect(document.activeElement).toBe(input)

      // Type — each keystroke re-renders Parent with a new inline onClose
      // closure. Before the fix this caused the effect to re-run and steal
      // focus back to the panel on every keystroke.
      fireEvent.change(input, { target: { value: 'a' } })
      fireEvent.change(input, { target: { value: 'ab' } })
      fireEvent.change(input, { target: { value: 'abc' } })

      // Flush any pending microtasks (the focus move uses queueMicrotask).
      await Promise.resolve()

      expect(document.activeElement).toBe(input)
      expect(input.value).toBe('abc')
    })
  })
})
