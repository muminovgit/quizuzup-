import { type FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, setToken } from '../api'

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const res = await api.login(username.trim(), password)
      setToken(res.token)
      navigate('/quizzes', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Xatolik yuz berdi')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-brand-start to-brand-end px-4">
      <div className="card w-full max-w-sm rounded-2xl shadow-xl p-8">
        <div className="flex justify-center mb-4">
          <span className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-start to-brand-end text-3xl text-white shadow-lg">
            ❓
          </span>
        </div>
        <h1 className="text-xl font-bold text-center mb-1">QuizUzup</h1>
        <p className="text-sm text-center mb-6" style={{ color: 'var(--text-muted)' }}>
          Testlarni yechish uchun tizimga kiring
        </p>

        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Login</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoComplete="username"
              className="w-full rounded-lg border px-3 py-2 outline-none focus:ring-2 focus:ring-brand-start"
              style={{ borderColor: 'var(--border)', background: 'var(--bg)' }}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Parol</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
              className="w-full rounded-lg border px-3 py-2 outline-none focus:ring-2 focus:ring-brand-start"
              style={{ borderColor: 'var(--border)', background: 'var(--bg)' }}
            />
          </div>

          {error && (
            <p className="text-sm text-red-500 bg-red-500/10 rounded-lg px-3 py-2">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-gradient-to-r from-brand-start to-brand-end text-white font-semibold py-2.5 disabled:opacity-60 transition-opacity"
          >
            {loading ? 'Kirilmoqda...' : 'Kirish'}
          </button>
        </form>

        <p className="text-xs text-center mt-6" style={{ color: 'var(--text-muted)' }}>
          Login va parolni Telegram botdan (/webportal buyrug'i) olasiz.
        </p>
      </div>
    </div>
  )
}
