import { apiFetch } from './client'

export type FlagReason = 'wrong_answer' | 'confusing' | 'seen_before' | 'too_hard'

export async function flagQuestion(
  idToken: string,
  questionId: string,
  reason: FlagReason,
  note: string,
  submittedAnswer: string,
): Promise<void> {
  await apiFetch(`/questions/${questionId}/flag`, idToken, {
    method: 'POST',
    body: JSON.stringify({ reason, note, submittedAnswer }),
  })
}
