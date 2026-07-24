import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <div
      style={{
        textAlign: 'center',
        padding: '64px 24px',
      }}
    >
      <h1 style={{ fontSize: '2rem', marginBottom: '8px' }}>404</h1>
      <p style={{ color: 'var(--ff-page-text-muted)', marginBottom: '20px' }}>
        The page you're looking for doesn't exist.
      </p>
      <Link to="/jobs">← Back to jobs</Link>
    </div>
  )
}
