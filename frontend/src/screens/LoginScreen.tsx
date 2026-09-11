import { useRef, useState, type FormEvent, type KeyboardEvent } from 'react'

import { useAuth } from '../auth/AuthContext'

const PIN_LENGTH = 6

export function LoginScreen() {
  const { signIn } = useAuth()
  const [username, setUsername] = useState('')
  const [digits, setDigits] = useState<string[]>(Array(PIN_LENGTH).fill(''))
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const digitRefs = useRef<(HTMLInputElement | null)[]>([])

  function setDigit(index: number, value: string) {
    const digit = value.replace(/\D/g, '').slice(-1)
    setDigits((prev) => prev.map((d, i) => (i === index ? digit : d)))
    if (digit && index < PIN_LENGTH - 1) {
      digitRefs.current[index + 1]?.focus()
    }
  }

  function handleKeyDown(index: number, event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Backspace' && !digits[index] && index > 0) {
      digitRefs.current[index - 1]?.focus()
    }
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)

    const pin = digits.join('')
    if (!username.trim() || pin.length !== PIN_LENGTH) {
      setError('Enter your username and all six digits of your PIN.')
      return
    }

    setIsSubmitting(true)
    try {
      await signIn(username.trim(), pin)
    } catch {
      setError("That didn't work — check the username and PIN and try again.")
      setDigits(Array(PIN_LENGTH).fill(''))
      digitRefs.current[0]?.focus()
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="centered-screen">
      <form onSubmit={handleSubmit} className="auth-card">
        <div>
          <h1>Axiom</h1>
          <p style={{ color: 'var(--ink-muted)', marginTop: '0.3rem' }}>Coordinate Geometry of the Line</p>
        </div>

        <div>
          <label htmlFor="username">Username</label>
          <input
            id="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            style={{ display: 'block', width: '100%', marginTop: '0.3rem' }}
          />
        </div>

        <div>
          <label id="pin-label">PIN</label>
          <div className="pin-input" role="group" aria-labelledby="pin-label" style={{ marginTop: '0.3rem' }}>
            {digits.map((digit, index) => (
              <input
                key={index}
                ref={(el) => {
                  digitRefs.current[index] = el
                }}
                value={digit}
                onChange={(e) => setDigit(index, e.target.value)}
                onKeyDown={(e) => handleKeyDown(index, e)}
                inputMode="numeric"
                maxLength={1}
                aria-label={`PIN digit ${index + 1}`}
              />
            ))}
          </div>
        </div>

        {error && (
          <p role="alert" className="feedback-wrong">
            {error}
          </p>
        )}

        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Logging in…' : 'Log in'}
        </button>
      </form>
    </main>
  )
}
