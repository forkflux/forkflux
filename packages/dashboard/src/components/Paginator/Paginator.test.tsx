import { describe, expect, it, vi } from 'vitest'
import { act, fireEvent, screen } from '@testing-library/react'
import { Paginator } from './Paginator'
import { renderWithRouter } from '../../test/utils'

describe('Paginator', () => {
  describe('range text', () => {
    it('shows "Showing X–Y of Z" for a full page', () => {
      renderWithRouter(
        <Paginator total={25} limit={10} offset={0} onOffsetChange={vi.fn()} onLimitChange={vi.fn()} />,
      )
      expect(screen.getByText('Showing 1–10 of 25')).toBeInTheDocument()
    })

    it('shows partial range on the last page', () => {
      renderWithRouter(
        <Paginator total={25} limit={10} offset={20} onOffsetChange={vi.fn()} onLimitChange={vi.fn()} />,
      )
      expect(screen.getByText('Showing 21–25 of 25')).toBeInTheDocument()
    })

    it('shows "Showing 0 results" when total is 0', () => {
      renderWithRouter(
        <Paginator total={0} limit={10} offset={0} onOffsetChange={vi.fn()} onLimitChange={vi.fn()} />,
      )
      expect(screen.getByText('Showing 0 results')).toBeInTheDocument()
    })
  })

  describe('prev/next buttons', () => {
    it('disables prev on the first page', () => {
      renderWithRouter(
        <Paginator total={25} limit={10} offset={0} onOffsetChange={vi.fn()} onLimitChange={vi.fn()} />,
      )
      expect(screen.getByLabelText('Previous page')).toBeDisabled()
    })

    it('enables prev on a non-first page', () => {
      renderWithRouter(
        <Paginator total={25} limit={10} offset={10} onOffsetChange={vi.fn()} onLimitChange={vi.fn()} />,
      )
      expect(screen.getByLabelText('Previous page')).not.toBeDisabled()
    })

    it('disables next on the last page', () => {
      renderWithRouter(
        <Paginator total={25} limit={10} offset={20} onOffsetChange={vi.fn()} onLimitChange={vi.fn()} />,
      )
      expect(screen.getByLabelText('Next page')).toBeDisabled()
    })

    it('enables next on a non-last page', () => {
      renderWithRouter(
        <Paginator total={25} limit={10} offset={0} onOffsetChange={vi.fn()} onLimitChange={vi.fn()} />,
      )
      expect(screen.getByLabelText('Next page')).not.toBeDisabled()
    })

    it('calls onOffsetChange with offset - limit when prev is clicked', () => {
      const onOffsetChange = vi.fn()
      renderWithRouter(
        <Paginator total={25} limit={10} offset={10} onOffsetChange={onOffsetChange} onLimitChange={vi.fn()} />,
      )
      fireEvent.click(screen.getByLabelText('Previous page'))
      expect(onOffsetChange).toHaveBeenCalledWith(0)
    })

    it('calls onOffsetChange with offset + limit when next is clicked', () => {
      const onOffsetChange = vi.fn()
      renderWithRouter(
        <Paginator total={25} limit={10} offset={0} onOffsetChange={onOffsetChange} onLimitChange={vi.fn()} />,
      )
      fireEvent.click(screen.getByLabelText('Next page'))
      expect(onOffsetChange).toHaveBeenCalledWith(10)
    })
  })

  describe('page buttons', () => {
    it('renders all page numbers when totalPages <= 7', () => {
      renderWithRouter(
        <Paginator total={50} limit={10} offset={0} onOffsetChange={vi.fn()} onLimitChange={vi.fn()} />,
      )
      // Pages 1-5
      expect(screen.getByText('1')).toBeInTheDocument()
      expect(screen.getByText('2')).toBeInTheDocument()
      expect(screen.getByText('3')).toBeInTheDocument()
      expect(screen.getByText('4')).toBeInTheDocument()
      expect(screen.getByText('5')).toBeInTheDocument()
      // No ellipsis
      expect(screen.queryByText('…')).not.toBeInTheDocument()
    })

    it('renders ellipsis when totalPages > 7', () => {
      renderWithRouter(
        <Paginator total={200} limit={10} offset={0} onOffsetChange={vi.fn()} onLimitChange={vi.fn()} />,
      )
      // First page always visible (as a page button, not the select option)
      const pageButtons = screen
        .getAllByText('1')
        .filter((el) => el.tagName === 'BUTTON')
      expect(pageButtons.length).toBeGreaterThan(0)
      // Last page (20) always visible as a page button
      const lastPageButtons = screen
        .getAllByText('20')
        .filter((el) => el.tagName === 'BUTTON')
      expect(lastPageButtons.length).toBeGreaterThan(0)
      // Ellipsis present
      expect(screen.getAllByText('…').length).toBeGreaterThan(0)
    })

    it('marks the current page as active with aria-current', () => {
      renderWithRouter(
        <Paginator total={50} limit={10} offset={10} onOffsetChange={vi.fn()} onLimitChange={vi.fn()} />,
      )
      const activeButton = screen.getByText('2')
      expect(activeButton).toHaveAttribute('aria-current', 'page')
      expect(activeButton).toHaveClass('ff-paginator__page--active')
    })

    it('calls onOffsetChange with (page - 1) * limit when a page is clicked', () => {
      const onOffsetChange = vi.fn()
      renderWithRouter(
        <Paginator total={50} limit={10} offset={0} onOffsetChange={onOffsetChange} onLimitChange={vi.fn()} />,
      )
      fireEvent.click(screen.getByText('3'))
      expect(onOffsetChange).toHaveBeenCalledWith(20)
    })
  })

  describe('offset clamping sync', () => {
    it('calls onOffsetChange with the clamped offset when offset is out of range', () => {
      const onOffsetChange = vi.fn()
      renderWithRouter(
        <Paginator
          total={25}
          limit={10}
          offset={40}
          onOffsetChange={onOffsetChange}
          onLimitChange={vi.fn()}
        />,
      )
      // total=25, limit=10 → 3 pages; offset=40 → page 5, clamped to page 3 (offset 20)
      expect(onOffsetChange).toHaveBeenCalledWith(20)
    })

    it('clamps to 0 when total is 0 and offset is non-zero', () => {
      const onOffsetChange = vi.fn()
      renderWithRouter(
        <Paginator
          total={0}
          limit={10}
          offset={40}
          onOffsetChange={onOffsetChange}
          onLimitChange={vi.fn()}
        />,
      )
      expect(onOffsetChange).toHaveBeenCalledWith(0)
    })

    it('does not call onOffsetChange on mount when the offset is already valid', () => {
      const onOffsetChange = vi.fn()
      renderWithRouter(
        <Paginator
          total={25}
          limit={10}
          offset={0}
          onOffsetChange={onOffsetChange}
          onLimitChange={vi.fn()}
        />,
      )
      expect(onOffsetChange).not.toHaveBeenCalled()
    })

    it('does not call onOffsetChange when offset is the last valid page', () => {
      const onOffsetChange = vi.fn()
      renderWithRouter(
        <Paginator
          total={25}
          limit={10}
          offset={20}
          onOffsetChange={onOffsetChange}
          onLimitChange={vi.fn()}
        />,
      )
      expect(onOffsetChange).not.toHaveBeenCalled()
    })

    it('does not loop: after clamping, a re-render with the clamped offset fires no further call', () => {
      const onOffsetChange = vi.fn()
      const { rerender } = renderWithRouter(
        <Paginator
          total={25}
          limit={10}
          offset={40}
          onOffsetChange={onOffsetChange}
          onLimitChange={vi.fn()}
        />,
      )
      // Initial mount clamps 40 → 20 (one call).
      expect(onOffsetChange).toHaveBeenCalledTimes(1)
      expect(onOffsetChange).toHaveBeenCalledWith(20)

      // Simulate the parent applying the clamped offset back.
      act(() => {
        rerender(
          <Paginator
            total={25}
            limit={10}
            offset={20}
            onOffsetChange={onOffsetChange}
            onLimitChange={vi.fn()}
          />,
        )
      })
      // No additional call once the offset is valid.
      expect(onOffsetChange).toHaveBeenCalledTimes(1)
    })
  })

  describe('page-size select', () => {
    it('renders all page-size options', () => {
      renderWithRouter(
        <Paginator total={25} limit={10} offset={0} onOffsetChange={vi.fn()} onLimitChange={vi.fn()} />,
      )
      const select = screen.getByRole('combobox')
      expect(select).toBeInTheDocument()
      // Options: 10, 20, 50, 100
      expect(screen.getByText('10')).toBeInTheDocument()
      expect(screen.getByText('20')).toBeInTheDocument()
      expect(screen.getByText('50')).toBeInTheDocument()
      expect(screen.getByText('100')).toBeInTheDocument()
    })

    it('calls onLimitChange when the page size is changed', () => {
      const onLimitChange = vi.fn()
      renderWithRouter(
        <Paginator total={25} limit={10} offset={0} onOffsetChange={vi.fn()} onLimitChange={onLimitChange} />,
      )
      fireEvent.change(screen.getByRole('combobox'), { target: { value: '20' } })
      expect(onLimitChange).toHaveBeenCalledWith(20)
    })
  })
})
