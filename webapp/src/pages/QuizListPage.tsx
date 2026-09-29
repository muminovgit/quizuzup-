import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type QuizSummary } from '../api'

export default function QuizListPage() {
  const [quizzes, setQuizzes] = useState<QuizSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .listQuizzes()
      .then(setQuizzes)
      .catch((err) => setError(err instanceof Error ? err.message : 'Xatolik'))
  }, [])

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Testlar</h1>
      <p className="mb-6" style={{ color: 'var(--text-muted)' }}>
        Yechish uchun testni tanlang
      </p>

      {error && <p className="text-red-500">{error}</p>}
      {quizzes === null && !error && <p style={{ color: 'var(--text-muted)' }}>Yuklanmoqda...</p>}
      {quizzes && quizzes.length === 0 && (
        <p style={{ color: 'var(--text-muted)' }}>Hozircha testlar mavjud emas.</p>
      )}

      <div className="grid gap-3 sm:grid-cols-2">
        {quizzes?.map((quiz) => (
          <Link
            key={quiz.quiz_id}
            to={`/quizzes/${quiz.quiz_id}`}
            className="card rounded-xl p-5 shadow-sm hover:shadow-md transition-shadow flex items-center justify-between"
          >
            <div>
              <div className="font-semibold">{quiz.name}</div>
              <div className="text-sm" style={{ color: 'var(--text-muted)' }}>
                {quiz.question_count} ta savol
              </div>
            </div>
            <span className="text-brand-start text-xl">→</span>
          </Link>
        ))}
      </div>
    </div>
  )
}
