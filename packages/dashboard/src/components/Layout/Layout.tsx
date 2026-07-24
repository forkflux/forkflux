import { Outlet } from 'react-router-dom'
import { Header } from '../Header/Header'
import './Layout.scss'

export function Layout() {
  return (
    <div className="ff-layout">
      <Header />
      <main className="ff-layout__main">
        <Outlet />
      </main>
    </div>
  )
}
