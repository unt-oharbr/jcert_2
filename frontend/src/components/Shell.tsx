import type { ReactNode } from 'react'

import { useAuth } from '../auth/AuthContext'

interface ShellProps {
  children: ReactNode
}

// The persistent frame around authenticated screens — a slim top bar
// instead of repeating a centered "card" pattern on every screen.
export function Shell({ children }: ShellProps) {
  const { signOut } = useAuth()

  return (
    <div className="app-shell">
      <header className="app-topbar">
        <span className="app-wordmark">Axiom</span>
        <button type="button" className="quiet" onClick={signOut}>
          Log out
        </button>
      </header>
      <div className="app-content">
        <div className="app-content-inner">{children}</div>
      </div>
    </div>
  )
}
