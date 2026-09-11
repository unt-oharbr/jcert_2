import { apiFetch } from './client'

export interface WorkedExample {
  title: string
  explanation: string
  example: string
}

export async function getWorkedExample(idToken: string, subtopic: string): Promise<WorkedExample> {
  return apiFetch<WorkedExample>(`/diagnostic/${subtopic}`, idToken)
}
