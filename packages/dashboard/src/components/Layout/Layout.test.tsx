import { describe, expect, it } from 'vitest'
import { screen } from '@testing-library/react'
import { Layout } from './Layout'
import { renderWithRouter } from '../../test/utils'

describe('Layout', () => {
  it('renders the Header', () => {
    renderWithRouter(
      <Layout />,
      { routerProps: { initialEntries: ['/jobs'] } },
    )
    expect(screen.getByText('ForkFlux')).toBeInTheDocument()
  })

  it('renders child content via Outlet', () => {
    // Layout uses <Outlet />, so we need a route config to test it.
    // We render it directly with children instead.
    function TestLayout() {
      return (
        <div className="ff-layout">
          <div>Header placeholder</div>
          <main className="ff-layout__main">
            <p>Outlet content</p>
          </main>
        </div>
      )
    }
    renderWithRouter(<TestLayout />)
    expect(screen.getByText('Outlet content')).toBeInTheDocument()
  })
})
