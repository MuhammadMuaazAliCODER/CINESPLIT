import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import api, { setAccessToken } from '../services/api'
import { getCurrentUser, loginAccount, logoutAccount, refreshSession } from '../services/auth'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const clearAuth = useCallback(() => {
    setAccessToken(null)
    setUser(null)
  }, [])

  useEffect(() => {
    let active = true
    refreshSession()
      .then(({ data }) => {
        if (!active) return
        setAccessToken(data.access_token)
        return getCurrentUser().then((profile) => { if (active) setUser(profile.data) })
      })
      .catch(() => { if (active) clearAuth() })
      .finally(() => { if (active) setLoading(false) })

    const onExpired = () => clearAuth()
    window.addEventListener('cinesplit:auth-expired', onExpired)
    return () => {
      active = false
      window.removeEventListener('cinesplit:auth-expired', onExpired)
    }
  }, [clearAuth])

  const signIn = useCallback(async (credentials) => {
    const { data } = await loginAccount(credentials)
    setAccessToken(data.access_token)
    setUser(data.user)
    return data.user
  }, [])

  const signOut = useCallback(async () => {
    try { await logoutAccount() } catch { /* local state is cleared even if the server is unreachable */ }
    clearAuth()
  }, [clearAuth])

  const value = useMemo(() => ({ user, loading, signIn, signOut, setUser }), [user, loading, signIn, signOut])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used within AuthProvider')
  return value
}
