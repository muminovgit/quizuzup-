// ?? not ||: an empty string is a deliberate "same origin as the page"
// setting (production, frontend and API served by the same host) and must
// not fall through to the localhost default.
export const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

const TOKEN_KEY = 'quizuzup_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> | undefined),
  }
  if (token) headers.Authorization = `Bearer ${token}`

  const res = await fetch(`${API_URL}${path}`, { ...options, headers })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail || detail
    } catch {
      // ignore
    }
    throw new ApiError(res.status, detail)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export interface Option {
  index: number
  text: string
}

export interface QuizSummary {
  quiz_id: number
  name: string
  question_count: number
}

export interface Question {
  question_id: number
  question_text: string
  options: Option[]
}

export interface QuizDetail {
  quiz_id: number
  name: string
  questions: Question[]
}

export interface SubmitResult {
  question_id: number
  correct: boolean
  correct_option: number
  explanation: string | null
}

export interface SubmitResponse {
  score: number
  total: number
  results: SubmitResult[]
}

export interface AnswerResult {
  correct: boolean
  correct_option: number
  explanation: string | null
}

export interface Mistake {
  question_id: number
  quiz_id: number
  quiz_name: string
  question_text: string
  options: Option[]
  selected_option: number
  correct_option: number
  explanation: string | null
}

export const api = {
  login: (username: string, password: string) =>
    request<{ token: string; username: string }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),
  me: () => request<{ username: string; user_id: number }>('/api/me'),
  listQuizzes: () => request<QuizSummary[]>('/api/quizzes'),
  getQuiz: (id: number) => request<QuizDetail>(`/api/quizzes/${id}`),
  submitQuiz: (id: number, answers: { question_id: number; selected_option: number }[]) =>
    request<SubmitResponse>(`/api/quizzes/${id}/submit`, {
      method: 'POST',
      body: JSON.stringify({ answers }),
    }),
  answerQuestion: (quizId: number, questionId: number, selectedOption: number) =>
    request<AnswerResult>(`/api/quizzes/${quizId}/questions/${questionId}/answer`, {
      method: 'POST',
      body: JSON.stringify({ selected_option: selectedOption }),
    }),
  mistakes: () => request<Mistake[]>('/api/mistakes'),
  retryMistake: (questionId: number, selectedOption: number) =>
    request<AnswerResult>(`/api/mistakes/${questionId}/retry`, {
      method: 'POST',
      body: JSON.stringify({ selected_option: selectedOption }),
    }),
}
