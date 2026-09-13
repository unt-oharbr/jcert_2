import { useEffect, useState } from 'react'

import type { Profile } from '../api/profile'
import { getProgress, type ProgressSummary } from '../api/progress'
import { ProgressBar } from '../components/ProgressBar'
import { AVATAR_GLYPH, COLOUR_SWATCH } from '../lib/appearance'
import { downloadReminderIcs } from '../lib/reminderIcs'

interface DashboardProps {
  profile: Profile
  idToken: string
  onStartSession: () => void
  onEditProfile: () => void
  refreshKey: number
}

export function Dashboard({ profile, idToken, onStartSession, onEditProfile, refreshKey }: DashboardProps) {
  const [progress, setProgress] = useState<ProgressSummary | null>(null)
  const [reminderTime, setReminderTime] = useState('17:00')

  useEffect(() => {
    getProgress(idToken)
      .then(setProgress)
      .catch(() => setProgress(null))
  }, [idToken, refreshKey])

  return (
    <>
      <div className="stat-row">
        <span
          className="swatch-avatar"
          aria-hidden="true"
          style={{ cursor: 'default', background: `${COLOUR_SWATCH[profile.colourTheme]}22` }}
        >
          {AVATAR_GLYPH[profile.avatar]}
        </span>
        <h1>Hey, {profile.nickname}</h1>
        <button type="button" className="quiet" onClick={onEditProfile} style={{ marginLeft: 'auto' }}>
          Edit profile
        </button>
      </div>

      {progress && (
        <div className="card">
          <div className="stat-row">
            <span className="stat-number">🔥 {progress.dailyStreak}</span>
            <span className="stat-label">day streak · best {progress.longestStreak}</span>
          </div>

          <div style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
            <ProgressBar label="Overall" fraction={progress.overallProgress} />
            {progress.topics.map((topic) => (
              <div key={topic.topicId}>
                <ProgressBar label={topic.label} fraction={topic.progress} />
                <div className="badge-row" style={{ marginTop: '0.4rem' }}>
                  <span className="badge">Tier: {topic.tier}</span>
                  {topic.introBadgeEarned && <span className="badge">🥉 First win</span>}
                  {topic.masteryBadgeEarned && <span className="badge">🏆 Mastered</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <button type="button" onClick={onStartSession} style={{ alignSelf: 'flex-start' }}>
        Start today's practice
      </button>

      <div className="card">
        <h2>Daily reminder</h2>
        <p className="stat-label" style={{ marginTop: '0.4rem' }}>
          Downloads a calendar file — open it afterwards to add the reminder to your calendar app.
        </p>
        <div className="answer-row" style={{ marginTop: '0.6rem' }}>
          <input
            id="reminder-time"
            type="time"
            value={reminderTime}
            onChange={(e) => setReminderTime(e.target.value)}
            style={{ flex: 'none' }}
          />
          <button type="button" className="secondary" onClick={() => downloadReminderIcs(reminderTime)}>
            Download reminder
          </button>
        </div>
      </div>
    </>
  )
}
