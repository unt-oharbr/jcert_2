import { apiFetch } from './client'

export interface TopicProgress {
  topicId: string
  label: string
  tier: string
  progress: number
  introBadgeEarned: boolean
  masteryBadgeEarned: boolean
  questionsAnswered: number
}

export interface ProgressSummary {
  topics: TopicProgress[]
  overallProgress: number
  dailyStreak: number
  longestStreak: number
}

export async function getProgress(idToken: string): Promise<ProgressSummary> {
  return apiFetch<ProgressSummary>('/progress', idToken)
}
