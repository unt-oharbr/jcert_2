import type { CognitoUserSession } from 'amazon-cognito-identity-js'
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

import { getCurrentSession, signIn as cognitoSignIn, signOut as cognitoSignOut } from './cognitoAuth'

interface AuthContextValue {
  isLoading: boolean
  isAuthenticated: boolean
  idToken: string | null
  signIn: (username: string, pin: string) => Promise<void>
  signOut: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isLoading, setIsLoading] = useState(true)
  const [session, setSession] = useState<CognitoUserSession | null>(null)

  useEffect(() => {
    getCurrentSession()
      .then(setSession)
      .catch(() => setSession(null))
      .finally(() => setIsLoading(false))
  }, [])

  const signIn = useCallback(async (username: string, pin: string) => {
    const newSession = await cognitoSignIn(username, pin)
    setSession(newSession)
  }, [])

  const signOut = useCallback(() => {
    cognitoSignOut()
    setSession(null)
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      isLoading,
      isAuthenticated: session !== null,
      idToken: session?.getIdToken().getJwtToken() ?? null,
      signIn,
      signOut,
    }),
    [isLoading, session, signIn, signOut],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}
