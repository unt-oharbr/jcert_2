import { useEffect, useState } from 'react'

import { getProfile, putProfile, type Profile } from './api/profile'
import { AuthProvider, useAuth } from './auth/AuthContext'
import { Shell } from './components/Shell'
import { Dashboard } from './screens/Dashboard'
import { LoginScreen } from './screens/LoginScreen'
import { ProfileSetupScreen } from './screens/ProfileSetupScreen'
import { SessionScreen } from './screens/SessionScreen'

function Loading() {
  return (
    <main className="centered-screen">
      <p>Loading…</p>
    </main>
  )
}

function AppShell() {
  const { isLoading, isAuthenticated, idToken } = useAuth()
  const [profile, setProfile] = useState<Profile | null>(null)
  const [isProfileNew, setIsProfileNew] = useState(false)
  const [isProfileLoading, setIsProfileLoading] = useState(true)
  const [inSession, setInSession] = useState(false)
  const [isEditingProfile, setIsEditingProfile] = useState(false)
  const [progressRefreshKey, setProgressRefreshKey] = useState(0)

  useEffect(() => {
    if (!idToken) return
    setIsProfileLoading(true)
    getProfile(idToken)
      .then((result) => {
        if (result.isNew) {
          setIsProfileNew(true)
        } else {
          setProfile(result as Profile)
        }
      })
      .finally(() => setIsProfileLoading(false))
  }, [idToken])

  if (isLoading) return <Loading />
  if (!isAuthenticated || !idToken) return <LoginScreen />
  if (isProfileLoading) return <Loading />

  if (isProfileNew || !profile) {
    return (
      <ProfileSetupScreen
        onSave={async (update) => {
          const saved = await putProfile(idToken, update)
          setProfile(saved)
          setIsProfileNew(false)
        }}
      />
    )
  }

  if (isEditingProfile) {
    return (
      <ProfileSetupScreen
        initialProfile={profile}
        onCancel={() => setIsEditingProfile(false)}
        onSave={async (update) => {
          const saved = await putProfile(idToken, update)
          setProfile(saved)
          setIsEditingProfile(false)
        }}
      />
    )
  }

  if (inSession) {
    return (
      <Shell>
        <SessionScreen
          idToken={idToken}
          onExit={() => {
            setInSession(false)
            setProgressRefreshKey((n) => n + 1)
          }}
        />
      </Shell>
    )
  }

  return (
    <Shell>
      <Dashboard
        profile={profile}
        idToken={idToken}
        onStartSession={() => setInSession(true)}
        onEditProfile={() => setIsEditingProfile(true)}
        refreshKey={progressRefreshKey}
      />
    </Shell>
  )
}

function App() {
  return (
    <AuthProvider>
      <AppShell />
    </AuthProvider>
  )
}

export default App
