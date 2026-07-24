import { describe, expect, it } from 'vitest'
import { screen } from '@testing-library/react'
import { NotFoundPage } from './NotFoundPage'
import { renderWithRouter } from '../../test/utils'

describe('NotFoundPage', () => {
  it('renders a 404 heading', () => {
    renderWithRouter(<NotFoundPage />)
    expect(screen.getByText('404')).toBeInTheDocument()
  })

  it('renders a descriptive message', () => {
    renderWithRouter(<NotFoundPage />)
    expect(
      screen.getByText(/doesn't exist/i),
    ).toBeInTheDocument()
  })

  it('renders a link back to /jobs', () => {
    renderWithRouter(<NotFoundPage />)
    const link = screen.getByText('← Back to jobs')
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute('href', '/jobs')
  })
})
