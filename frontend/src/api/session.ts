import { apiFetch } from './client'

export interface LineVisualization {
  pointA: [number, number]
  pointB: [number, number]
  anchorPoint?: [number, number]
  mode?: 'parallel' | 'perpendicular'
  displayMode?: 'line' | 'segment-slope' | 'segment-midpoint' | 'segment-distance' | 'line-intercept'
}

export interface NextQuestion {
  questionId: string
  topicId: string
  topicLabel: string
  subtopic: string
  difficulty: string
  type: string
  answerType: string
  prompt: string
  visualization: LineVisualization | null
}

export interface DiagnosticOffer {
  available: boolean
  prerequisiteNodeId: string
  nudge: boolean
}

export interface AnswerResult {
  correct: boolean
  correctAnswer: string
  diagnosticOffer: DiagnosticOffer | null
  progress: {
    tier: string
    introBadgeEarned: boolean
    masteryBadgeEarned: boolean
  }
  dailyStreak: number
  questionsToday: number
}

interface RetrySameSubtopic {
  topicId: string
  subtopic: string
}

export async function getNextQuestion(idToken: string, retry?: RetrySameSubtopic): Promise<NextQuestion> {
  return apiFetch<NextQuestion>('/session/next-question', idToken, {
    method: 'POST',
    body: retry ? JSON.stringify(retry) : undefined,
  })
}

export async function submitAnswer(idToken: string, questionId: string, answer: string): Promise<AnswerResult> {
  return apiFetch<AnswerResult>('/session/answer', idToken, {
    method: 'POST',
    body: JSON.stringify({ questionId, answer }),
  })
}
