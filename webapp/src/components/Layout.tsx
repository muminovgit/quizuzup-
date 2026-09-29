import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { clearToken } from '../api'

export default function Layout() {
  const navigate = useNavigate()

  function logout() {
    clearToken()
    navigate('/login', { replace: true })
  }

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
      isActive
        ? 'bg-white/20 text-white'
        : 'text-white/80 hover:text-white hover:bg-white/10'
    }`

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-gradient-to-r from-brand-start to-brand-end">
        <div className="max-w-4xl mx-auto flex items-center justify-between px-4 py-3">
          <div className="flex items-center gap-2 text-white font-bold text-lg">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-xl bg-white/20 text-xl">
              ❓
            </span>
            QuizUzup
          </div>
          <nav className="flex items-center gap-1">
            <NavLink to="/quizzes" className={linkClass}>
              Testlar
            </NavLink>
            <NavLink to="/mistakes" className={linkClass}>
              Xatolarim
            </NavLink>
            <button
              onClick={logout}
              className="px-3 py-2 rounded-lg text-sm font-medium text-white/80 hover:text-white hover:bg-white/10 transition-colors"
            >
              Chiqish
            </button>
          </nav>
        </div>
      </header>
      <main className="flex-1 max-w-4xl w-full mx-auto px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
