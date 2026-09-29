import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, type QuizDetail, type SubmitResponse } from '../api'

export default function QuizTakePage() {
  const { id } = useParams()
  const quizId = Number(id)

  const [quiz, setQuiz] = useState<QuizDetail | null>(null)
  const [answers, setAnswers] = useState<Record<number, number>>({})
  const [result, setResult] = useState<SubmitResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    setQuiz(null)
    setAnswers({})
    setResult(null)
    api
      .getQuiz(quizId)
      .then(setQuiz)
      .catch((err) => setError(err instanceof Error ? err.message : 'Xatolik'))
  }, [quizId])

  function pick(questionId: number, optionIndex: number) {
    if (result) return
    setAnswers((prev) => ({ ...prev, [questionId]: optionIndex }))
  }

  async function submit() {
    if (!quiz) return
    setSubmitting(true)
    setError(null)
    try {
      const payload = Object.entries(answers).map(([qid, selected]) => ({
        question_id: Number(qid),
        selected_option: selected,
      }))
      const res = await api.submitQuiz(quiz.quiz_id, payload)
      setResult(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Xatolik')
    } finally {
      setSubmitting(false)
    }
  }

  if (error) return <p className="text-red-500">{error}</p>
  if (!quiz) return <p style={{ color: 'var(--text-muted)' }}>Yuklanmoqda...</p>

  const resultByQuestion = new Map(result?.results.map((r) => [r.question_id, r]))
  const allAnswered = quiz.questions.every((q) => answers[q.question_id] !== undefined)

  return (
    <div>
      <Link to="/quizzes" className="text-sm text-brand-start font-medium">
        ← Testlar
      </Link>
      <h1 className="text-2xl font-bold mt-2 mb-1">{quiz.name}</h1>

      {result && (
        <div className="card rounded-xl p-4 my-4 flex items-center gap-3">
          <span className="text-3xl">{result.score === result.total ? '🎉' : '📊'}</span>
          <div>
            <div className="font-semibold">
              Natija: {result.score} / {result.total}
            </div>
            <div className="text-sm" style={{ color: 'var(--text-muted)' }}>
              Xato javoblar "Xatolarim" bo'limida saqlandi.
            </div>
          </div>
        </div>
      )}

      <div className="space-y-5 mt-4">
        {quiz.questions.map((q, qi) => {
          const picked = answers[q.question_id]
          const r = resultByQuestion.get(q.question_id)
          return (
            <div key={q.question_id} className="card rounded-xl p-5">
              <div className="font-medium mb-3">
                {qi + 1}. {q.question_text}
              </div>
              <div className="grid gap-2">
                {q.options.map((opt) => {
                  const isPicked = picked === opt.index
                  let stateClass = 'border-transparent'
                  if (result && r) {
                    if (opt.index === r.correct_option) {
                      stateClass = 'border-green-500 bg-green-500/10'
                    } else if (isPicked && !r.correct) {
                      stateClass = 'border-red-500 bg-red-500/10'
                    }
                  } else if (isPicked) {
                    stateClass = 'border-brand-start bg-brand-start/10'
                  }
                  return (
                    <button
                      key={opt.index}
                      type="button"
                      disabled={!!result}
                      onClick={() => pick(q.question_id, opt.index)}
                      className={`text-left rounded-lg border-2 px-4 py-2.5 transition-colors ${stateClass} disabled:cursor-default`}
                      style={{ background: stateClass === 'border-transparent' ? 'var(--bg)' : undefined }}
                    >
                      {opt.text}
                    </button>
                  )
                })}
              </div>
              {result && r && r.explanation && (
                <p className="text-sm mt-3" style={{ color: 'var(--text-muted)' }}>
                  💡 {r.explanation}
                </p>
              )}
            </div>
          )
        })}
      </div>

      {!result && (
        <button
          onClick={submit}
          disabled={!allAnswered || submitting}
          className="w-full mt-6 rounded-lg bg-gradient-to-r from-brand-start to-brand-end text-white font-semibold py-3 disabled:opacity-50 transition-opacity"
        >
          {submitting ? 'Yuborilmoqda...' : 'Yakunlash'}
        </button>
      )}

      {result && (
        <Link
          to="/quizzes"
          className="block w-full mt-6 text-center rounded-lg border-2 font-semibold py-3"
          style={{ borderColor: 'var(--border)' }}
        >
          Testlar ro'yxatiga qaytish
        </Link>
      )}
    </div>
  )
}
