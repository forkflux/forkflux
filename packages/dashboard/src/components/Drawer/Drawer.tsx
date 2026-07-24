import { useEffect, useRef, type ReactNode } from 'react'
import './Drawer.scss'

interface DrawerProps {
  open: boolean
  onClose: () => void
  title?: string
  width?: string
  children: ReactNode
}

/**
 * Reusable slide-in drawer panel.
 *
 * Renders a right-side overlay panel with backdrop, ESC-to-close, body scroll
 * lock, and focus management. All behavior is self-contained — no external
 * dialog library dependency.
 */
export function Drawer({ open, onClose, title, width = '75%', children }: DrawerProps) {
  const panelRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<Element | null>(null)

  // ESC to close + body scroll lock while open.
  useEffect(() => {
    if (!open) return

    triggerRef.current = document.activeElement

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation()
        onClose()
      }
    }

    document.addEventListener('keydown', onKeyDown)
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    // Move focus into the panel.
    queueMicrotask(() => {
      panelRef.current?.focus()
    })

    return () => {
      document.removeEventListener('keydown', onKeyDown)
      document.body.style.overflow = prevOverflow
      // Restore focus to the element that opened the drawer.
      if (triggerRef.current instanceof HTMLElement) {
        triggerRef.current.focus()
      }
    }
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="ff-drawer" role="presentation">
      <div
        className="ff-drawer__overlay"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        ref={panelRef}
        className="ff-drawer__panel"
        style={{ width }}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
      >
        {title && (
          <div className="ff-drawer__header">
            <h2 className="ff-drawer__title">{title}</h2>
            <button
              type="button"
              className="ff-drawer__close"
              onClick={onClose}
              aria-label="Close"
            >
              ×
            </button>
          </div>
        )}
        <div className="ff-drawer__body">{children}</div>
      </div>
    </div>
  )
}
