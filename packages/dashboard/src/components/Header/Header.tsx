import { NavLink } from 'react-router-dom'
import { ThemeToggle } from '../ThemeToggle/ThemeToggle'
import './Header.scss'

export function Header() {
  return (
    <header className="ff-header">
      <div className="ff-header__inner">
        <NavLink to="/jobs" className="ff-header__brand">
          <img
            src="/logos/colored-logo.svg"
            alt="ForkFlux"
            className="ff-header__logo"
          />
          <span className="ff-header__title">ForkFlux</span>
        </NavLink>

        <nav className="ff-header__nav">
          <NavLink
            to="/jobs"
            className={({ isActive }) =>
              `ff-header__nav-link${isActive ? ' ff-header__nav-link--active' : ''}`
            }
          >
            Jobs
          </NavLink>

          <ThemeToggle />
        </nav>
      </div>
    </header>
  )
}
