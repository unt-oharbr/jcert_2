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
  // null while a same-question retry is offered — nothing is resolved yet,
  // so there is nothing to reveal.
  correctAnswer: string | null
  // True only on a wrong first attempt eligible for a retry: the question
  // isn't resolved, nothing else in this response reflects a real change.
  secondAttemptAvailable: boolean
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

export async function getNextQuestion(
  idToken: string,
  sessionId: string,
  retry?: RetrySameSubtopic,
): Promise<NextQuestion> {
  return apiFetch<NextQuestion>('/session/next-question', idToken, {
    method: 'POST',
    body: JSON.stringify({ sessionId, ...retry }),
  })
}

export async function submitAnswer(
  idToken: string,
  sessionId: string,
  questionId: string,
  answer: string,
  millisecondsSinceShown: number,
): Promise<AnswerResult> {
  return apiFetch<AnswerResult>('/session/answer', idToken, {
    method: 'POST',
    body: JSON.stringify({ sessionId, questionId, answer, millisecondsSinceShown }),
  })
}
