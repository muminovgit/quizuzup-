import type { ReactElement } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { getToken } from './api'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
import MistakesPage from './pages/MistakesPage'
import QuizListPage from './pages/QuizListPage'
import QuizTakePage from './pages/QuizTakePage'

function RequireAuth({ children }: { children: ReactElement }) {
  if (!getToken()) return <Navigate to="/login" replace />
  return children
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route path="/quizzes" element={<QuizListPage />} />
        <Route path="/quizzes/:id" element={<QuizTakePage />} />
        <Route path="/mistakes" element={<MistakesPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/quizzes" replace />} />
    </Routes>
  )
}

export default App
