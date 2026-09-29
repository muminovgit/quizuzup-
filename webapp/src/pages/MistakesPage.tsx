import { useEffect, useState } from 'react'
import { api, type Mistake } from '../api'

type RetryState = { correct: boolean; correct_option: number; explanation: string | null } | null

export default function MistakesPage() {
  const [mistakes, setMistakes] = useState<Mistake[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [retryResults, setRetryResults] = useState<Record<number, RetryState>>({})
  const [picked, setPicked] = useState<Record<number, number>>({})

  function load() {
    api
      .mistakes()
      .then(setMistakes)
      .catch((err) => setError(err instanceof Error ? err.message : 'Xatolik'))
  }

  useEffect(load, [])

  async function retry(questionId: number) {
    const selected = picked[questionId]
    if (selected === undefined) return
    try {
      const res = await api.retryMistake(questionId, selected)
      setRetryResults((prev) => ({ ...prev, [questionId]: res }))
      if (res.correct) {
        setTimeout(load, 900)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Xatolik')
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Xatolarim</h1>
      <p className="mb-6" style={{ color: 'var(--text-muted)' }}>
        Noto'g'ri javob bergan savollaringiz. To'g'ri javob bersangiz, ro'yxatdan chiqib ketadi.
      </p>

      {error && <p className="text-red-500">{error}</p>}
      {mistakes === null && !error && <p style={{ color: 'var(--text-muted)' }}>Yuklanmoqda...</p>}
      {mistakes && mistakes.length === 0 && (
        <div className="card rounded-xl p-6 text-center">
          <div className="text-3xl mb-2">🎉</div>
          <p style={{ color: 'var(--text-muted)' }}>Xatolaringiz yo'q. Ajoyib!</p>
        </div>
      )}

      <div className="space-y-5">
        {mistakes?.map((m) => {
          const retryResult = retryResults[m.question_id]
          const selected = picked[m.question_id] ?? m.selected_option
          return (
            <div key={m.question_id} className="card rounded-xl p-5">
              <div className="text-xs font-medium text-brand-start mb-1">{m.quiz_name}</div>
              <div className="font-medium mb-3">{m.question_text}</div>
              <div className="grid gap-2">
                {m.options.map((opt) => {
                  const isPicked = selected === opt.index
                  let stateClass = 'border-transparent'
                  if (retryResult) {
                    if (opt.index === retryResult.correct_option) {
                      stateClass = 'border-green-500 bg-green-500/10'
                    } else if (isPicked && !retryResult.correct) {
                      stateClass = 'border-red-500 bg-red-500/10'
                    }
                  } else if (isPicked) {
                    stateClass = 'border-brand-start bg-brand-start/10'
                  }
                  return (
                    <button
                      key={opt.index}
                      type="button"
                      disabled={!!retryResult?.correct}
                      onClick={() => setPicked((prev) => ({ ...prev, [m.question_id]: opt.index }))}
                      className={`text-left rounded-lg border-2 px-4 py-2.5 transition-colors ${stateClass}`}
                      style={{ background: stateClass === 'border-transparent' ? 'var(--bg)' : undefined }}
                    >
                      {opt.text}
                    </button>
                  )
                })}
              </div>

              {retryResult?.explanation && (
                <p className="text-sm mt-3" style={{ color: 'var(--text-muted)' }}>
                  💡 {retryResult.explanation}
                </p>
              )}

              {!retryResult?.correct && (
                <button
                  onClick={() => retry(m.question_id)}
                  className="mt-3 rounded-lg bg-brand-start text-white text-sm font-semibold px-4 py-2"
                >
                  Qayta yechish
                </button>
              )}
              {retryResult?.correct && (
                <p className="text-sm mt-3 text-green-500 font-medium">✅ To'g'ri! Ro'yxatdan chiqmoqda...</p>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
