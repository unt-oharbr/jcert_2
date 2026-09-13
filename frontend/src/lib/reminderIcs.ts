// A daily-repeating calendar reminder, generated entirely client-side —
// no backend involved. Real Web Push was ruled out for Phase 0: it needs
// VAPID signing and encrypted payloads (real cryptography with compiled
// extensions, breaking the pure-Python Lambda Layer this project otherwise
// uses everywhere), a subscription-storage table, and a scheduled Lambda —
// a lot of new infrastructure just to say "time to practice."

function pad(n: number): string {
  return n.toString().padStart(2, '0')
}

export function buildReminderIcs(time: string): string {
  const [hours, minutes] = time.split(':').map(Number)
  const today = new Date()
  const dateStr = `${today.getFullYear()}${pad(today.getMonth() + 1)}${pad(today.getDate())}`
  const startTime = `${pad(hours)}${pad(minutes)}00`

  return [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//Axiom//Daily Practice Reminder//EN',
    'BEGIN:VEVENT',
    'UID:axiom-daily-practice-reminder@localhost',
    `DTSTAMP:${dateStr}T000000Z`,
    `DTSTART:${dateStr}T${startTime}`,
    'DURATION:PT15M',
    'RRULE:FREQ=DAILY',
    'SUMMARY:Axiom — Maths practice time',
    'DESCRIPTION:Time for your daily Maths practice.',
    'BEGIN:VALARM',
    'TRIGGER:PT0M',
    'ACTION:DISPLAY',
    'DESCRIPTION:Axiom practice time',
    'END:VALARM',
    'END:VEVENT',
    'END:VCALENDAR',
  ].join('\r\n')
}

export function downloadReminderIcs(time: string): void {
  const ics = buildReminderIcs(time)
  const blob = new Blob([ics], { type: 'text/calendar' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'axiom-daily-practice-reminder.ics'
  link.click()
  URL.revokeObjectURL(url)
}
