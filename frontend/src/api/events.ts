import { config } from '../config'

export type FrontendEventType =
  | 'session_start'
  | 'session_end'
  | 'worked_example_shown'
  | 'worked_example_dismissed'
  | 'block_complete'

// Fire-and-forget instrumentation (T4) — invisible to her, never read back
// by any frontend code path. Errors are swallowed deliberately: nothing
// here is allowed to affect the question flow or surface as a UI failure,
// since a missed log entry is a non-event for her and not worth retrying.
export function logSessionEvent(
  idToken: string,
  sessionId: string,
  eventType: FrontendEventType,
  data: Record<string, unknown> = {},
): void {
  fetch(`${config.apiBaseUrl}/session/event`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${idToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ eventType, sessionId, ...data }),
  }).catch(() => {
    // Deliberately silent — see module docstring.
  })
}
