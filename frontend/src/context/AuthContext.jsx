/**
 * Authentication context.
 *
 * On app load: calls /auth/me ONCE to check if session cookie exists.
 */
import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { authApi, fetchCsrfToken } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const checkedRef = useRef(false)

  useEffect(() => {
    if (checkedRef.current) return
    checkedRef.current = true

    fetchCsrfToken()

    authApi
      .me()
      .then((res) => setUser(res.data))
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (email, password) => {
    const res = await authApi.login(email, password)
    await fetchCsrfToken()
    setUser(res.data.user)
  }, [])

  const register = useCallback(async (email, username, password) => {
    const res = await authApi.register(email, username, password)
    await fetchCsrfToken()
    setUser(res.data.user)
  }, [])

  const logout = useCallback(async () => {
    try {
      await authApi.logout()
    } catch (_) {
      // ignore network/logout errors and clear local auth state anyway
    }
    setUser(null)
    window.location.href = '/'
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
