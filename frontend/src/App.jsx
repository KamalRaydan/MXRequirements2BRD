import { Link, Route, Routes, useLocation } from 'react-router-dom'
import ErrorBoundary from './components/ErrorBoundary'
import ProjectList from './pages/ProjectList'
import ProjectDetail from './pages/ProjectDetail'
import Generate from './pages/Generate'
import Settings from './pages/Settings'

export default function App() {
  const location = useLocation()
  const onSettings = location.pathname === '/settings'

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <Link to="/" className="text-lg font-semibold tracking-tight">
            Maximo<span className="text-blue-600">BRD</span>
          </Link>
          <nav className="flex gap-4 text-sm">
            <Link to="/" className={!onSettings ? 'font-medium text-blue-600' : 'text-slate-600 hover:text-slate-900'}>
              Projects
            </Link>
            <Link to="/settings" className={onSettings ? 'font-medium text-blue-600' : 'text-slate-600 hover:text-slate-900'}>
              Settings
            </Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-8">
        <ErrorBoundary>
          <Routes>
            <Route path="/" element={<ProjectList />} />
            <Route path="/projects/:id" element={<ProjectDetail />} />
            <Route path="/projects/:id/generate" element={<Generate />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </ErrorBoundary>
      </main>
    </div>
  )
}
