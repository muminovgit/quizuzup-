import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, type AnswerResult, type QuizDetail } from '../api'

const OPTION_STYLES = [
  { idle: 'bg-blue-500 hover:bg-blue-600', ring: 'ring-blue-300' },
  { idle: 'bg-red-500 hover:bg-red-600', ring: 'ring-red-300' },
  { idle: 'bg-amber-500 hover:bg-amber-600', ring: 'ring-amber-300' },
  { idle: 'bg-emerald-500 hover:bg-emerald-600', ring: 'ring-emerald-300' },
]

export default function QuizTakePage() {
  const { id } = useParams()
  const quizId = Number(id)

  const [quiz, setQuiz] = useState<QuizDetail | null>(null)
  const [error, setError] = useState<string | null>(null)

  const [index, setIndex] = useState(0)
  const [selected, setSelected] = useState<number | null>(null)
  const [answerResult, setAnswerResult] = useState<AnswerResult | null>(null)
  const [score, setScore] = useState(0)
  const [finished, setFinished] = useState(false)
  const [answering, setAnswering] = useState(false)

  useEffect(() => {
    api
      .getQuiz(quizId)
      .then(setQuiz)
      .catch((err) => setError(err instanceof Error ? err.message : 'Xatolik'))
  }, [quizId])

  function resetForNewQuestion() {
    setSelected(null)
    setAnswerResult(null)
  }

  function restart() {
    setIndex(0)
    setScore(0)
    setFinished(false)
    resetForNewQuestion()
  }

  async function pick(optionIndex: number) {
    if (!quiz || answerResult || answering) return
    const question = quiz.questions[index]
    setSelected(optionIndex)
    setAnswering(true)
    try {
      const res = await api.answerQuestion(quiz.quiz_id, question.question_id, optionIndex)
      setAnswerResult(res)
      if (res.correct) setScore((s) => s + 1)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Xatolik')
    } finally {
      setAnswering(false)
    }
  }

  function next() {
    if (!quiz) return
    if (index + 1 < quiz.questions.length) {
      setIndex((i) => i + 1)
      resetForNewQuestion()
    } else {
      setFinished(true)
    }
  }

  if (error) return <p className="text-red-500">{error}</p>
  if (!quiz) return <p style={{ color: 'var(--text-muted)' }}>Yuklanmoqda...</p>

  const total = quiz.questions.length

  if (finished) {
    const pct = Math.round((score / total) * 100)
    const emoji = pct >= 80 ? '🎉' : pct >= 50 ? '👍' : '💪'
    return (
      <div className="min-h-[70vh] flex items-center justify-center">
        <div className="card rounded-3xl shadow-xl p-8 max-w-sm w-full text-center">
          <div className="text-6xl mb-3">{emoji}</div>
          <h1 className="text-2xl font-bold mb-1">Natija</h1>
          <p className="text-4xl font-extrabold text-brand-start my-3">
            {score} / {total}
          </p>
          <p className="mb-6" style={{ color: 'var(--text-muted)' }}>
            {pct}% to'g'ri javob
          </p>
          <div className="space-y-2">
            <button
              onClick={restart}
              className="w-full rounded-xl bg-gradient-to-r from-brand-start to-brand-end text-white font-semibold py-3"
            >
              Qayta yechish
            </button>
            <Link
              to="/quizzes"
              className="block w-full rounded-xl border-2 font-semibold py-3"
              style={{ borderColor: 'var(--border)' }}
            >
              Testlar ro'yxati
            </Link>
            <Link to="/mistakes" className="block text-sm text-brand-start font-medium pt-2">
              Xatolarimni ko'rish →
            </Link>
          </div>
        </div>
      </div>
    )
  }

  const question = quiz.questions[index]
  const progressPct = ((index + (answerResult ? 1 : 0)) / total) * 100

  return (
    <div className="max-w-lg mx-auto">
      <div className="flex items-center justify-between mb-2">
        <Link to="/quizzes" className="text-sm text-brand-start font-medium">
          ← Chiqish
        </Link>
        <span className="text-sm font-semibold" style={{ color: 'var(--text-muted)' }}>
          {index + 1} / {total}
        </span>
      </div>

      <div className="h-2 rounded-full overflow-hidden mb-6" style={{ background: 'var(--border)' }}>
        <div
          className="h-full rounded-full bg-gradient-to-r from-brand-start to-brand-end transition-all duration-300"
          style={{ width: `${progressPct}%` }}
        />
      </div>

      <div className="card rounded-2xl shadow-sm p-6 mb-5 min-h-[120px] flex items-center justify-center text-center">
        <p className="text-lg font-semibold leading-snug">{question.question_text}</p>
      </div>

      {answerResult && (
        <div
          className={`rounded-xl px-4 py-3 mb-4 font-semibold text-center text-white ${
            answerResult.correct ? 'bg-emerald-500' : 'bg-red-500'
          }`}
        >
          {answerResult.correct ? '✅ To\'g\'ri!' : '❌ Noto\'g\'ri'}
          {answerResult.explanation && (
            <p className="font-normal text-sm mt-1 opacity-90">💡 {answerResult.explanation}</p>
          )}
        </div>
      )}

      <div className="grid grid-cols-2 gap-3">
        {question.options.map((opt) => {
          const style = OPTION_STYLES[opt.index % OPTION_STYLES.length]
          const isSelected = selected === opt.index
          const isCorrectOption = answerResult && opt.index === answerResult.correct_option
          const isWrongPick = answerResult && isSelected && !answerResult.correct

          let extra = ''
          if (answerResult) {
            if (isCorrectOption) extra = 'ring-4 ring-white scale-105'
            else if (isWrongPick) extra = 'opacity-60 ring-4 ring-white'
            else extra = 'opacity-40'
          } else if (isSelected) {
            extra = `ring-4 ${style.ring}`
          }

          return (
            <button
              key={opt.index}
              type="button"
              disabled={!!answerResult || answering}
              onClick={() => pick(opt.index)}
              className={`min-h-[92px] rounded-2xl px-3 py-4 text-white font-semibold text-base leading-snug shadow-md transition-all active:scale-95 disabled:cursor-default ${style.idle} ${extra}`}
            >
              {isCorrectOption && '✓ '}
              {isWrongPick && '✕ '}
              {opt.text}
            </button>
          )
        })}
      </div>

      {answerResult && (
        <button
          onClick={next}
          className="w-full mt-5 rounded-xl bg-gradient-to-r from-brand-start to-brand-end text-white font-semibold py-3.5"
        >
          {index + 1 < total ? 'Keyingisi →' : 'Yakunlash'}
        </button>
      )}
    </div>
  )
}
