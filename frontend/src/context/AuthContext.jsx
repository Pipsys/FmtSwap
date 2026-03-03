/**
 * Authentication context.
 * 
 * On app load: calls /auth/me ONCE to check if session cookie exists.
 * 401 on that call = not logged in = show login page. NO retry, NO loop.
 */
import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react'
import { authApi, fetchCsrfToken } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const checkedRef = useRef(false)  // ensure we only check once

  useEffect(() => {
    if (checkedRef.current) return
    checkedRef.current = true

    // Pre-fetch CSRF token in parallel with session check
    fetchCsrfToken()

    authApi.me()
      .then((res) => setUser(res.data))
      .catch(() => {
        // 401 = no valid session. This is NORMAL for logged-out users.
        // Do nothing — just leave user as null.
        setUser(null)
      })
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (email, password) => {
    const res = await authApi.login(email, password)
    await fetchCsrfToken()  // refresh CSRF after login
    setUser(res.data.user)
  }, [])

  const register = useCallback(async (email, username, password) => {
    const res = await authApi.register(email, username, password)
    await fetchCsrfToken()
    setUser(res.data.user)
  }, [])

  const logout = useCallback(async () => {
    try { await authApi.logout() } catch (_) {}
    setUser(null)
    window.location.href = '/login'
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
