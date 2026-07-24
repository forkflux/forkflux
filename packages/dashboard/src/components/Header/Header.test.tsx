import { describe, expect, it } from 'vitest'
import { screen } from '@testing-library/react'
import { Header } from './Header'
import { renderWithRouter } from '../../test/utils'

describe('Header', () => {
  it('renders the ForkFlux brand title', () => {
    renderWithRouter(<Header />)
    expect(screen.getByText('ForkFlux')).toBeInTheDocument()
  })

  it('renders the logo image', () => {
    renderWithRouter(<Header />)
    expect(screen.getByAltText('ForkFlux')).toBeInTheDocument()
  })

  it('renders a Jobs nav link', () => {
    renderWithRouter(<Header />)
    expect(screen.getByText('Jobs')).toBeInTheDocument()
  })

  it('renders a Roles nav link', () => {
    renderWithRouter(<Header />)
    const link = screen.getByText('Roles')
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute('href', '/roles')
  })

  it('renders an Agents nav link', () => {
    renderWithRouter(<Header />)
    const link = screen.getByText('Agents')
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute('href', '/agents')
  })

  it('renders the theme toggle button', () => {
    renderWithRouter(<Header />)
    expect(screen.getByRole('button', { name: /theme/i })).toBeInTheDocument()
  })
})
