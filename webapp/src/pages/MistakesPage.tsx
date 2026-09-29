import { useEffect, useState } from 'react'
import { api, type AnswerResult, type Mistake } from '../api'

const OPTION_STYLES = [
  { idle: 'bg-blue-500 hover:bg-blue-600', ring: 'ring-blue-300' },
  { idle: 'bg-red-500 hover:bg-red-600', ring: 'ring-red-300' },
  { idle: 'bg-amber-500 hover:bg-amber-600', ring: 'ring-amber-300' },
  { idle: 'bg-emerald-500 hover:bg-emerald-600', ring: 'ring-emerald-300' },
]

export default function MistakesPage() {
  const [mistakes, setMistakes] = useState<Mistake[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [results, setResults] = useState<Record<number, AnswerResult>>({})
  const [picked, setPicked] = useState<Record<number, number>>({})

  function load() {
    api
      .mistakes()
      .then(setMistakes)
      .catch((err) => setError(err instanceof Error ? err.message : 'Xatolik'))
  }

  useEffect(load, [])

  async function retry(questionId: number, optionIndex: number) {
    if (results[questionId]) return
    setPicked((prev) => ({ ...prev, [questionId]: optionIndex }))
    try {
      const res = await api.retryMistake(questionId, optionIndex)
      setResults((prev) => ({ ...prev, [questionId]: res }))
      if (res.correct) setTimeout(load, 1000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Xatolik')
    }
  }

  return (
    <div className="max-w-lg mx-auto">
      <h1 className="text-2xl font-bold mb-1">Xatolarim</h1>
      <p className="mb-6" style={{ color: 'var(--text-muted)' }}>
        Noto'g'ri javob bergan savollaringiz. To'g'ri javob bersangiz, ro'yxatdan chiqib ketadi.
      </p>

      {error && <p className="text-red-500">{error}</p>}
      {mistakes === null && !error && <p style={{ color: 'var(--text-muted)' }}>Yuklanmoqda...</p>}
      {mistakes && mistakes.length === 0 && (
        <div className="card rounded-2xl p-8 text-center">
          <div className="text-4xl mb-2">🎉</div>
          <p style={{ color: 'var(--text-muted)' }}>Xatolaringiz yo'q. Ajoyib!</p>
        </div>
      )}

      <div className="space-y-6">
        {mistakes?.map((m) => {
          const result = results[m.question_id]
          const selected = picked[m.question_id] ?? m.selected_option

          return (
            <div key={m.question_id} className="card rounded-2xl shadow-sm p-5">
              <div className="text-xs font-bold text-brand-start mb-1 uppercase tracking-wide">
                {m.quiz_name}
              </div>
              <p className="font-semibold mb-4">{m.question_text}</p>

              {result && (
                <div
                  className={`rounded-xl px-4 py-3 mb-4 font-semibold text-center text-white ${
                    result.correct ? 'bg-emerald-500' : 'bg-red-500'
                  }`}
                >
                  {result.correct ? '✅ To\'g\'ri!' : '❌ Yana noto\'g\'ri'}
                  {result.explanation && (
                    <p className="font-normal text-sm mt-1 opacity-90">💡 {result.explanation}</p>
                  )}
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                {m.options.map((opt) => {
                  const style = OPTION_STYLES[opt.index % OPTION_STYLES.length]
                  const isSelected = selected === opt.index
                  const isCorrectOption = result && opt.index === result.correct_option
                  const isWrongPick = result && isSelected && !result.correct

                  let extra = ''
                  if (result) {
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
                      disabled={!!result}
                      onClick={() => retry(m.question_id, opt.index)}
                      className={`min-h-[80px] rounded-2xl px-3 py-3 text-white font-semibold text-sm leading-snug shadow-md transition-all active:scale-95 disabled:cursor-default ${style.idle} ${extra}`}
                    >
                      {isCorrectOption && '✓ '}
                      {isWrongPick && '✕ '}
                      {opt.text}
                    </button>
                  )
                })}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
