import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout/Layout'
import { OnboardingGuard } from './components/OnboardingGuard/OnboardingGuard'
import { OnboardingPage } from './pages/OnboardingPage/OnboardingPage'
import { JobListPage } from './pages/JobListPage/JobListPage'
import { JobDetailPage } from './pages/JobDetailPage/JobDetailPage'
import { RolesPage } from './pages/RolesPage/RolesPage'
import { AgentsPage } from './pages/AgentsPage/AgentsPage'
import { NotFoundPage } from './pages/NotFoundPage/NotFoundPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<OnboardingGuard />}>
          {/* Onboarding page — rendered outside the main Layout so the
              header nav links are hidden during setup. */}
          <Route path="/onboarding" element={<OnboardingPage />} />

          <Route element={<Layout />}>
            <Route index element={<Navigate to="/jobs" replace />} />
            <Route path="/jobs" element={<JobListPage />} />
            <Route path="/jobs/:id" element={<JobDetailPage />} />
            <Route path="/roles" element={<RolesPage />} />
            <Route path="/agents" element={<AgentsPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
