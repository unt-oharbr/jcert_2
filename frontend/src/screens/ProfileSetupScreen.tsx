import { useState, type FormEvent } from 'react'

import type { AvatarId, ColourTheme } from '../api/profile'
import { AVATAR_GLYPH, COLOUR_SWATCH } from '../lib/appearance'

const AVATARS: AvatarId[] = ['fox', 'owl', 'otter', 'comet', 'cactus', 'wave']
const COLOUR_THEMES: ColourTheme[] = ['indigo', 'coral', 'teal', 'amber', 'violet']

interface ProfileSetupScreenProps {
  onSave: (update: { nickname: string; avatar: AvatarId; colourTheme: ColourTheme }) => Promise<void>
  // Present only when reopening an existing profile to edit it — first-run
  // setup has nothing to pre-fill and nowhere to cancel back to.
  initialProfile?: { nickname: string; avatar: AvatarId; colourTheme: ColourTheme }
  onCancel?: () => void
}

export function ProfileSetupScreen({ onSave, initialProfile, onCancel }: ProfileSetupScreenProps) {
  const isEditing = Boolean(initialProfile)
  const [nickname, setNickname] = useState(initialProfile?.nickname ?? '')
  const [avatar, setAvatar] = useState<AvatarId>(initialProfile?.avatar ?? AVATARS[0]!)
  const [colourTheme, setColourTheme] = useState<ColourTheme>(initialProfile?.colourTheme ?? COLOUR_THEMES[0]!)
  const [error, setError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    if (!nickname.trim()) {
      setError('Pick a nickname first.')
      return
    }
    setIsSaving(true)
    try {
      await onSave({ nickname: nickname.trim(), avatar, colourTheme })
    } catch {
      setError("Couldn't save that — try again.")
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <main className="centered-screen">
      <form onSubmit={handleSubmit} className="auth-card">
        <div>
          <h1>{isEditing ? 'Your profile' : 'Make it yours'}</h1>
          <p style={{ color: 'var(--ink-muted)', marginTop: '0.3rem' }}>
            {isEditing
              ? 'Update your nickname, avatar or colour.'
              : 'This is your profile — pick whatever you like, change it any time.'}
          </p>
        </div>

        <div>
          <label htmlFor="nickname">Nickname</label>
          <input
            id="nickname"
            value={nickname}
            onChange={(e) => setNickname(e.target.value)}
            maxLength={20}
            style={{ display: 'block', width: '100%', marginTop: '0.3rem' }}
          />
        </div>

        <div>
          <label id="avatar-label">Avatar</label>
          <div role="radiogroup" aria-labelledby="avatar-label" className="swatch-grid" style={{ marginTop: '0.4rem' }}>
            {AVATARS.map((option) => (
              <button
                type="button"
                key={option}
                className="swatch-avatar"
                aria-pressed={avatar === option}
                aria-label={option}
                onClick={() => setAvatar(option)}
              >
                {AVATAR_GLYPH[option]}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label id="colour-label">Colour</label>
          <div role="radiogroup" aria-labelledby="colour-label" className="swatch-grid" style={{ marginTop: '0.4rem' }}>
            {COLOUR_THEMES.map((option) => (
              <button
                type="button"
                key={option}
                className="swatch-colour"
                style={{ background: COLOUR_SWATCH[option] }}
                aria-pressed={colourTheme === option}
                aria-label={option}
                onClick={() => setColourTheme(option)}
              />
            ))}
          </div>
        </div>

        {error && (
          <p role="alert" className="feedback-wrong">
            {error}
          </p>
        )}

        <button type="submit" disabled={isSaving}>
          {isSaving ? 'Saving…' : isEditing ? 'Save' : "Let's go"}
        </button>
        {isEditing && onCancel && (
          <button type="button" className="quiet" onClick={onCancel} disabled={isSaving}>
            Cancel
          </button>
        )}
      </form>
    </main>
  )
}
